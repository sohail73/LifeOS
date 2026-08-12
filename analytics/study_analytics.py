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
