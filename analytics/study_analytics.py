"""
analytics/study_analytics.py

Pandas-based aggregations over a user's study_sessions data. Every
function takes the raw sessions DataFrame (from
database.queries.get_study_sessions_df) so the same data isn't
re-queried repeatedly on one page render.

Expected columns: id, date (datetime64), duration_minutes, source,
notes, subject.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd

from utils.helper import calculate_streak


def total_minutes(df: pd.DataFrame) -> float:
    return float(df["duration_minutes"].sum()) if not df.empty else 0.0


def minutes_on_date(df: pd.DataFrame, day: date) -> float:
    if df.empty:
        return 0.0
    mask = df["date"].dt.date == day
    return float(df.loc[mask, "duration_minutes"].sum())


def minutes_since(df: pd.DataFrame, since: date) -> float:
    if df.empty:
        return 0.0
    mask = df["date"].dt.date >= since
    return float(df.loc[mask, "duration_minutes"].sum())


def get_streaks(df: pd.DataFrame) -> tuple[int, int]:
    """(current_streak, longest_streak) in days, based on study activity."""
    if df.empty:
        return 0, 0
    return calculate_streak(df["date"])


def subject_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Total minutes per subject, sorted descending."""
    if df.empty:
        return pd.DataFrame(columns=["subject", "duration_minutes"])
    result = (
        df.groupby("subject")["duration_minutes"]
        .sum()
        .reset_index()
        .sort_values("duration_minutes", ascending=False)
    )
    return result


def daily_totals(df: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    """
    Study minutes per calendar day for the last `days` days, with
    zero-filled gaps so charts don't skip inactive days.
    """
    end = date.today()
    start = end - timedelta(days=days - 1)
    all_days = pd.date_range(start, end, freq="D")

    if df.empty:
        return pd.DataFrame({"date": all_days, "duration_minutes": 0.0})

    daily = (
        df[df["date"].dt.date >= start]
        .groupby(df["date"].dt.date)["duration_minutes"]
        .sum()
    )
    daily.index = pd.to_datetime(daily.index)
    result = daily.reindex(all_days, fill_value=0.0).reset_index()
    result.columns = ["date", "duration_minutes"]
    return result


def monthly_totals(df: pd.DataFrame, months: int = 12) -> pd.DataFrame:
    """
    Study minutes per calendar month for the last `months` months
    (including the current one), zero-filled so a month with no
    sessions still shows up as 0 instead of being skipped. Columns:
    month (Period), month_label ("Jun 2026"), duration_minutes.
    """
    end_period = pd.Period(date.today(), freq="M")
    periods = pd.period_range(end=end_period, periods=months, freq="M")

    if df.empty:
        grouped = pd.Series(0.0, index=periods)
    else:
        working = df.copy()
        working["year_month"] = working["date"].dt.to_period("M")
        grouped = working.groupby("year_month")["duration_minutes"].sum()
        grouped = grouped.reindex(periods, fill_value=0.0)

    result = grouped.reset_index()
    result.columns = ["month", "duration_minutes"]
    result["month_label"] = result["month"].dt.strftime("%b %Y")
    return result


def yearly_totals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Study minutes per calendar year, for every year that has at least
    one session. Columns: year (str), duration_minutes.
    """
    if df.empty:
        return pd.DataFrame(columns=["year", "duration_minutes"])

    working = df.copy()
    working["year"] = working["date"].dt.year
    grouped = working.groupby("year")["duration_minutes"].sum().reset_index()
    grouped = grouped.sort_values("year")
    grouped["year"] = grouped["year"].astype(str)
    return grouped


def weekday_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Average minutes studied per day-of-week, Monday first."""
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if df.empty:
        return pd.DataFrame({"weekday": order, "avg_minutes": [0.0] * 7})

    df = df.copy()
    df["weekday"] = df["date"].dt.day_name()
    grouped = df.groupby("weekday")["duration_minutes"].mean()
    result = grouped.reindex(order, fill_value=0.0).reset_index()
    result.columns = ["weekday", "avg_minutes"]
    return result


def best_and_worst_weekday(df: pd.DataFrame) -> tuple[str | None, str | None]:
    totals = weekday_totals(df)
    if totals["avg_minutes"].sum() == 0:
        return None, None
    best = totals.loc[totals["avg_minutes"].idxmax(), "weekday"]
    worst = totals.loc[totals["avg_minutes"].idxmin(), "weekday"]
    return best, worst


def week_over_week_growth(df: pd.DataFrame) -> float | None:
    """% change in study minutes this week (last 7 days) vs previous 7 days."""
    if df.empty:
        return None
    today = date.today()
    this_start = today - timedelta(days=6)
    prev_start = today - timedelta(days=13)
    prev_end = today - timedelta(days=7)

    this_week = minutes_since(df, this_start)
    prev_week = float(
        df[(df["date"].dt.date >= prev_start) & (df["date"].dt.date <= prev_end)][
            "duration_minutes"
        ].sum()
    )

    if prev_week == 0:
        return None  # no baseline to compare against
    return float(np.round((this_week - prev_week) / prev_week * 100, 1))


def month_over_month_growth(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    df = df.copy()
    df["year_month"] = df["date"].dt.to_period("M")
    monthly = df.groupby("year_month")["duration_minutes"].sum().sort_index()

    if len(monthly) < 2:
        return None
    current, previous = monthly.iloc[-1], monthly.iloc[-2]
    if previous == 0:
        return None
    return float(np.round((current - previous) / previous * 100, 1))


def heatmap_data(df: pd.DataFrame, days: int = 182) -> pd.DataFrame:
    """Daily study minutes for the last `days` days -- feeds the study heatmap."""
    return daily_totals(df, days=days)


def combined_streak(study_df: pd.DataFrame, coding_df: pd.DataFrame) -> tuple[int, int]:
    """
    Overall app-activity streak: a day counts as "active" if there was
    study time OR a solved problem that day (not just one or the
    other). (current_streak, longest_streak) in days.
    """
    active_dates: list = []
    if not study_df.empty:
        active_dates.extend(study_df["date"].dt.date.tolist())
    if not coding_df.empty:
        active_dates.extend(coding_df["date_solved"].dt.date.tolist())
    if not active_dates:
        return 0, 0
    return calculate_streak(pd.Series(active_dates))


def combined_daily_activity(study_df: pd.DataFrame, coding_df: pd.DataFrame, days: int = 182) -> pd.DataFrame:
    """
    Study hours + problems solved per day for the last `days` days,
    zero-filled -- feeds the Dashboard's overall app-activity heatmap
    (as opposed to a coding-only or study-only one).
    """
    end = date.today()
    start = end - timedelta(days=days - 1)
    all_days = pd.date_range(start, end, freq="D")

    daily_minutes = daily_totals(study_df, days=days).set_index("date")["duration_minutes"]

    if coding_df.empty:
        daily_problems = pd.Series(0, index=all_days)
    else:
        recent = coding_df[coding_df["date_solved"].dt.date >= start]
        grouped = recent.groupby(recent["date_solved"].dt.floor("D")).size()
        daily_problems = grouped.reindex(all_days, fill_value=0)

    result = pd.DataFrame({"date": all_days})
    result["hours"] = (daily_minutes.reindex(all_days, fill_value=0).values / 60).round(2)
    result["problems"] = daily_problems.values
    # Weighted activity score used only for heatmap color intensity --
    # each problem counts like roughly 20 minutes of focused work.
    result["score"] = result["hours"] * 60 + result["problems"] * 20
    return result
