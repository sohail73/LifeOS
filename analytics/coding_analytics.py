"""
analytics/coding_analytics.py

Pandas-based aggregations over a user's coding_logs data (from
database.queries.get_coding_logs_df).

Expected columns: id, platform, problem_name, language, difficulty,
topic, date_solved (datetime64), time_taken_minutes, notes.
"""

from datetime import date, timedelta

import pandas as pd

from utils.helper import calculate_streak


def total_problems(df: pd.DataFrame) -> int:
    return int(len(df))


def problems_on_date(df: pd.DataFrame, day: date) -> int:
    if df.empty:
        return 0
    return int((df["date_solved"].dt.date == day).sum())


def problems_since(df: pd.DataFrame, since: date) -> int:
    if df.empty:
        return 0
    return int((df["date_solved"].dt.date >= since).sum())


def get_streaks(df: pd.DataFrame) -> tuple[int, int]:
    if df.empty:
        return 0, 0
    return calculate_streak(df["date_solved"])


def language_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["language", "count", "percent"])
    counts = df["language"].value_counts().reset_index()
    counts.columns = ["language", "count"]
    counts["percent"] = (counts["count"] / counts["count"].sum() * 100).round(1)
    return counts


def difficulty_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["difficulty", "count"])
    order = ["Easy", "Medium", "Hard"]
    counts = df["difficulty"].value_counts().reindex(order, fill_value=0).reset_index()
    counts.columns = ["difficulty", "count"]
    return counts


def topic_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["topic", "count"])
    counts = df["topic"].value_counts().reset_index()
    counts.columns = ["topic", "count"]
    return counts.sort_values("count", ascending=False)


def average_solving_time(df: pd.DataFrame) -> float | None:
    if df.empty or df["time_taken_minutes"].dropna().empty:
        return None
    return float(df["time_taken_minutes"].dropna().mean())


def most_active_weekday(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    weekday_counts = df["date_solved"].dt.day_name().value_counts()
    if weekday_counts.empty:
        return None
    return weekday_counts.idxmax()


def language_trend(df: pd.DataFrame, days: int = 60) -> pd.DataFrame:
    """
    Daily problem count per language for the last `days` days, in
    long format (date, language, count) -- feeds the multi-line
    language trend chart. Zero-filled so every language has a point
    on every day in range.
    """
    end = date.today()
    start = end - timedelta(days=days - 1)
    all_days = pd.date_range(start, end, freq="D")

    if df.empty:
        return pd.DataFrame(columns=["date", "language", "count"])

    recent = df[df["date_solved"].dt.date >= start].copy()
    if recent.empty:
        return pd.DataFrame(columns=["date", "language", "count"])

    recent["day"] = recent["date_solved"].dt.floor("D")
    grouped = recent.groupby(["day", "language"]).size().reset_index(name="count")

    languages = grouped["language"].unique()
    full_index = pd.MultiIndex.from_product([all_days, languages], names=["day", "language"])
    result = (
        grouped.set_index(["day", "language"])
        .reindex(full_index, fill_value=0)
        .reset_index()
    )
    result.columns = ["date", "language", "count"]
    return result


def week_over_week_growth(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    today = date.today()
    this_week = problems_since(df, today - timedelta(days=6))
    prev_start = today - timedelta(days=13)
    prev_end = today - timedelta(days=7)
    prev_week = int(
        ((df["date_solved"].dt.date >= prev_start) & (df["date_solved"].dt.date <= prev_end)).sum()
    )
    if prev_week == 0:
        return None
    return round((this_week - prev_week) / prev_week * 100, 1)
