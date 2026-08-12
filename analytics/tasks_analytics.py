"""
analytics/tasks_analytics.py

Small aggregations over a user's tasks (from
database.queries.get_tasks_df) that power the Goals & Tasks page:
daily completion counts for the streak heatmap, the streak itself,
and progress against a specific long-term goal's date range.
"""

from datetime import date, datetime

import pandas as pd

from utils.helper import calculate_streak


def daily_completion_counts(tasks_df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-day count of completed tasks, for the streak heatmap. Expects
    columns: task_date (datetime64), is_done (bool).
    """
    if tasks_df.empty:
        return pd.DataFrame(columns=["task_date", "completed_count"])

    completed = tasks_df[tasks_df["is_done"]]
    if completed.empty:
        return pd.DataFrame(columns=["task_date", "completed_count"])

    grouped = completed.groupby(completed["task_date"].dt.floor("D")).size().reset_index()
    grouped.columns = ["task_date", "completed_count"]
    return grouped


def task_streak(tasks_df: pd.DataFrame) -> tuple[int, int]:
    """(current_streak, longest_streak) in days with at least one completed task."""
    if tasks_df.empty:
        return 0, 0
    completed_dates = tasks_df.loc[tasks_df["is_done"], "task_date"]
    if completed_dates.empty:
        return 0, 0
    return calculate_streak(completed_dates)


def goal_progress(goal: dict, tasks_df: pd.DataFrame) -> dict:
    """
    Completion stats for a single long-term goal: how many of its
    linked tasks are done, and where "today" sits in the goal's date
    range.
    """
    start = datetime.strptime(goal["start_date"], "%Y-%m-%d").date()
    end = datetime.strptime(goal["end_date"], "%Y-%m-%d").date()
    today = date.today()

    total_tasks = len(tasks_df)
    completed_tasks = int(tasks_df["is_done"].sum()) if not tasks_df.empty else 0
    completion_pct = round(completed_tasks / total_tasks * 100, 1) if total_tasks else 0.0

    total_days = (end - start).days + 1
    days_elapsed = max(0, min((today - start).days + 1, total_days))
    days_remaining = max(0, (end - today).days)

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "completion_pct": completion_pct,
        "total_days": total_days,
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "is_overdue": today > end and completion_pct < 100,
    }
