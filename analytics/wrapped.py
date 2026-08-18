"""
analytics/wrapped.py

Computes the numbers behind Monthly and Yearly Wrapped (product
spec sections 29-30) directly from study_sessions/coding_logs.
Wrapped is a live report, not stored data -- it always reflects
current numbers for the selected period.
"""

from datetime import date, timedelta

import pandas as pd

from analytics import coding_analytics as ca
from analytics import study_analytics as sa
from utils.helper import calculate_streak


def _filter_period(df: pd.DataFrame, date_col: str, start: date, end: date) -> pd.DataFrame:
    if df.empty:
        return df
    mask = (df[date_col].dt.date >= start) & (df[date_col].dt.date <= end)
    return df.loc[mask]


def monthly_wrapped(study_df: pd.DataFrame, coding_df: pd.DataFrame, year: int, month: int) -> dict:
    start = date(year, month, 1)
    end = date(year + (month // 12), (month % 12) + 1, 1) - timedelta(days=1)

    month_study = _filter_period(study_df, "date", start, end)
    month_coding = _filter_period(coding_df, "date_solved", start, end)

    study_hours = round(month_study["duration_minutes"].sum() / 60, 1) if not month_study.empty else 0.0
    total_problems = ca.total_problems(month_coding)

    lang_dist = ca.language_distribution(month_coding)
    top_language = lang_dist.iloc[0]["language"] if not lang_dist.empty else None

    subject_dist = sa.subject_breakdown(month_study)
    top_subject = subject_dist.iloc[0]["subject"] if not subject_dist.empty else None

    topic_dist = ca.topic_distribution(month_coding)
    top_topic = topic_dist.iloc[0]["topic"] if not topic_dist.empty else None
    weak_topic = topic_dist.iloc[-1]["topic"] if len(topic_dist) > 1 else None

    _, longest_streak = calculate_streak(month_study["date"]) if not month_study.empty else (0, 0)

    best_day, _ = sa.best_and_worst_weekday(month_study)

    return {
        "period_label": start.strftime("%B %Y"),
        "study_hours": study_hours,
        "problems_solved": total_problems,
        "top_language": top_language,
        "top_subject": top_subject,
        "top_topic": top_topic,
        "weakest_topic": weak_topic,
        "longest_streak": longest_streak,
        "best_day": best_day,
        "has_data": study_hours > 0 or total_problems > 0,
    }


def yearly_wrapped(study_df: pd.DataFrame, coding_df: pd.DataFrame, year: int) -> dict:
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    year_study = _filter_period(study_df, "date", start, end)
    year_coding = _filter_period(coding_df, "date_solved", start, end)

    study_hours = round(year_study["duration_minutes"].sum() / 60, 1) if not year_study.empty else 0.0
    total_problems = ca.total_problems(year_coding)

    lang_dist = ca.language_distribution(year_coding)
    top_language = lang_dist.iloc[0]["language"] if not lang_dist.empty else None

    topic_dist = ca.topic_distribution(year_coding)
    top_topic = topic_dist.iloc[0]["topic"] if not topic_dist.empty else None

    _, longest_streak = calculate_streak(year_study["date"]) if not year_study.empty else (0, 0)
    best_day, _ = sa.best_and_worst_weekday(year_study)

    best_month = None
    if not year_study.empty:
        monthly = year_study.groupby(year_study["date"].dt.month)["duration_minutes"].sum()
        if not monthly.empty:
            best_month_num = int(monthly.idxmax())
            best_month = date(year, best_month_num, 1).strftime("%B")

    return {
        "period_label": str(year),
        "study_hours": study_hours,
        "problems_solved": total_problems,
        "top_language": top_language,
        "top_topic": top_topic,
        "longest_streak": longest_streak,
        "best_day": best_day,
        "best_month": best_month,
        "has_data": study_hours > 0 or total_problems > 0,
    }


def get_available_months(study_df: pd.DataFrame, coding_df: pd.DataFrame) -> list[tuple[int, int]]:
    """
    Every (year, month) from the user's earliest recorded activity up
    to the current month, most recent first -- the month list for the
    "Your Journey" timeline. Empty if there's no data at all.
    """
    earliest_dates = []
    if not study_df.empty:
        earliest_dates.append(study_df["date"].min().date())
    if not coding_df.empty:
        earliest_dates.append(coding_df["date_solved"].min().date())
    if not earliest_dates:
        return []

    earliest = min(earliest_dates)
    cursor = date(earliest.year, earliest.month, 1)
    today = date.today()

    months = []
    while cursor <= today:
        months.append((cursor.year, cursor.month))
        cursor = date(cursor.year + (cursor.month // 12), (cursor.month % 12) + 1, 1)

    months.reverse()  # most recent first
    return months
