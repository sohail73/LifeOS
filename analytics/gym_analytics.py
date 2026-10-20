"""
analytics/gym_analytics.py

Pandas-based aggregations over a user's gym_sessions data (from
database.queries.get_gym_sessions_df).

Expected columns: id, date (datetime64), workout_type, duration_minutes, notes.
"""

from datetime import date, timedelta

import pandas as pd

from utils.helper import calculate_streak


def total_sessions(df: pd.DataFrame) -> int:
    return int(len(df))


def total_minutes(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return float(df["duration_minutes"].fillna(0).sum())


def sessions_since(df: pd.DataFrame, since: date) -> int:
    if df.empty:
        return 0
    return int((df["date"].dt.date >= since).sum())


def minutes_since(df: pd.DataFrame, since: date) -> float:
    if df.empty:
        return 0.0
    return float(df.loc[df["date"].dt.date >= since, "duration_minutes"].fillna(0).sum())


def get_streaks(df: pd.DataFrame) -> tuple[int, int]:
    if df.empty:
        return 0, 0
    return calculate_streak(df["date"])


def daily_counts(df: pd.DataFrame, days: int = 182) -> pd.DataFrame:
    """
    Workout minutes per calendar day for the last `days` days,
    zero-filled so the streak heatmap doesn't skip rest days.
    """
    end = date.today()
    start = end - timedelta(days=days - 1)
    all_days = pd.date_range(start, end, freq="D")

    if df.empty:
        return pd.DataFrame({"date": all_days, "duration_minutes": 0.0})

    recent = df[df["date"].dt.date >= start]
    daily = recent.groupby(recent["date"].dt.floor("D"))["duration_minutes"].sum()
    result = daily.reindex(all_days, fill_value=0.0).reset_index()
    result.columns = ["date", "duration_minutes"]
    return result


def workout_type_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["workout_type", "count"])
    result = df.groupby("workout_type").size().reset_index(name="count")
    return result.sort_values("count", ascending=False)


def sessions_this_week(df: pd.DataFrame) -> int:
    start_of_week = date.today() - timedelta(days=date.today().weekday())
    return sessions_since(df, start_of_week)
