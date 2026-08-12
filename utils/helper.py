"""
utils/helper.py

Small, generic helpers shared across pages and analytics modules:
duration formatting and streak calculation. Kept dependency-light
(pandas only) so it can be unit-tested without Streamlit.
"""

from datetime import date, timedelta

import pandas as pd


def format_duration(total_minutes: float) -> str:
    """Format minutes as e.g. '2h 20m', '45m', or '0m'."""
    total_minutes = int(round(total_minutes or 0))
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def calculate_streak(active_dates: pd.Series) -> tuple[int, int]:
    """
    Given a Series/iterable of dates (any date-like values) on which the
    user was active, return (current_streak, longest_streak) in days.

    current_streak counts consecutive active days ending today or
    yesterday (so a streak isn't broken just because today hasn't
    happened yet). longest_streak is the best run anywhere in the data.
    """
    if active_dates is None or len(active_dates) == 0:
        return 0, 0

    unique_days = sorted({pd.Timestamp(d).date() for d in active_dates})

    # Longest streak: walk through sorted unique days.
    longest = 1
    running = 1
    for prev, curr in zip(unique_days, unique_days[1:]):
        if curr - prev == timedelta(days=1):
            running += 1
            longest = max(longest, running)
        else:
            running = 1

    # Current streak: count backwards from today (or yesterday).
    day_set = set(unique_days)
    today = date.today()
    anchor = today if today in day_set else today - timedelta(days=1)

    current = 0
    cursor = anchor
    while cursor in day_set:
        current += 1
        cursor -= timedelta(days=1)

    return current, longest


def empty_state(icon: str, title: str, subtitle: str) -> str:
    """Return a small markdown block for a consistent empty-state message."""
    return f"### {icon} {title}\n\n{subtitle}"
