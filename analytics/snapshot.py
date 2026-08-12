"""
analytics/snapshot.py

Builds a frozen weekly/monthly snapshot from a user's current data
and stores it via database.queries.save_snapshot. Snapshots are the
basis for the Snapshots page, Time Machine-style comparisons, and
Wrapped -- they capture what the numbers looked like AT THE TIME,
so they don't silently change when new data comes in later.
"""

from datetime import date, timedelta

import pandas as pd

from analytics import coding_analytics as ca
from analytics import study_analytics as sa
from database.queries import (
    get_coding_logs_df,
    get_goals,
    get_study_sessions_df,
    save_snapshot,
)


def _goal_completion(study_df: pd.DataFrame, coding_df: pd.DataFrame, goals: dict, start: date, end: date) -> float:
    """
    Average daily goal completion (%) over the period, based on the
    user's current daily study-minutes and problems goals. Capped at
    100% per day so one huge day doesn't inflate the whole period.
    """
    num_days = (end - start).days + 1
    if num_days <= 0:
        return 0.0

    study_goal = max(goals.get("daily_study_minutes_goal", 60), 1)
    problems_goal = max(goals.get("daily_problems_goal", 2), 1)

    completions = []
    for offset in range(num_days):
        day = start + timedelta(days=offset)
        minutes = sa.minutes_on_date(study_df, day) if not study_df.empty else 0.0
        problems = ca.problems_on_date(coding_df, day) if not coding_df.empty else 0

        study_completion = min(minutes / study_goal, 1.0)
        problems_completion = min(problems / problems_goal, 1.0)
        completions.append((study_completion + problems_completion) / 2)

    return round(sum(completions) / len(completions) * 100, 1)


def build_and_save_weekly_snapshot(user_id: int, reference_day: date | None = None) -> dict:
    """Build the snapshot for the ISO week containing reference_day (default: today)."""
    reference_day = reference_day or date.today()
    start = reference_day - timedelta(days=reference_day.weekday())  # Monday
    end = start + timedelta(days=6)

    study_df = get_study_sessions_df(user_id)
    coding_df = get_coding_logs_df(user_id)
    goals = get_goals(user_id)

    period_mask_study = (
        (study_df["date"].dt.date >= start) & (study_df["date"].dt.date <= end)
        if not study_df.empty
        else pd.Series(dtype=bool)
    )
    period_mask_coding = (
        (coding_df["date_solved"].dt.date >= start) & (coding_df["date_solved"].dt.date <= end)
        if not coding_df.empty
        else pd.Series(dtype=bool)
    )

    study_hours = round(study_df.loc[period_mask_study, "duration_minutes"].sum() / 60, 2) if not study_df.empty else 0.0
    problems_solved = int(period_mask_coding.sum()) if not coding_df.empty else 0
    current_streak, _ = sa.get_streaks(study_df)
    goal_completion = _goal_completion(study_df, coding_df, goals, start, end)

    year, week_num, _ = start.isocalendar()
    period_label = f"{year}-W{week_num:02d}"

    save_snapshot(
        user_id=user_id,
        snapshot_type="weekly",
        period_label=period_label,
        period_start=start.isoformat(),
        period_end=end.isoformat(),
        study_hours=study_hours,
        problems_solved=problems_solved,
        current_streak=current_streak,
        goal_completion=goal_completion,
    )

    return {
        "period_label": period_label,
        "period_start": start,
        "period_end": end,
        "study_hours": study_hours,
        "problems_solved": problems_solved,
        "current_streak": current_streak,
        "goal_completion": goal_completion,
    }


def build_and_save_monthly_snapshot(user_id: int, reference_day: date | None = None) -> dict:
    """Build the snapshot for the calendar month containing reference_day (default: today)."""
    reference_day = reference_day or date.today()
    start = reference_day.replace(day=1)
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    end = next_month - timedelta(days=1)

    study_df = get_study_sessions_df(user_id)
    coding_df = get_coding_logs_df(user_id)
    goals = get_goals(user_id)

    period_mask_study = (
        (study_df["date"].dt.date >= start) & (study_df["date"].dt.date <= end)
        if not study_df.empty
        else pd.Series(dtype=bool)
    )
    period_mask_coding = (
        (coding_df["date_solved"].dt.date >= start) & (coding_df["date_solved"].dt.date <= end)
        if not coding_df.empty
        else pd.Series(dtype=bool)
    )

    study_hours = round(study_df.loc[period_mask_study, "duration_minutes"].sum() / 60, 2) if not study_df.empty else 0.0
    problems_solved = int(period_mask_coding.sum()) if not coding_df.empty else 0
    current_streak, _ = sa.get_streaks(study_df)
    goal_completion = _goal_completion(study_df, coding_df, goals, start, min(end, date.today()))

    period_label = start.strftime("%Y-%m")

    save_snapshot(
        user_id=user_id,
        snapshot_type="monthly",
        period_label=period_label,
        period_start=start.isoformat(),
        period_end=end.isoformat(),
        study_hours=study_hours,
        problems_solved=problems_solved,
        current_streak=current_streak,
        goal_completion=goal_completion,
    )

    return {
        "period_label": period_label,
        "period_start": start,
        "period_end": end,
        "study_hours": study_hours,
        "problems_solved": problems_solved,
        "current_streak": current_streak,
        "goal_completion": goal_completion,
    }
