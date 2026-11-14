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


def load_leave_dates() -> set:
    """
    The logged-in user's leave days (see Dashboard > App Streak > "Mark
    leave"), as a set of datetime.date. Looked up lazily so every
    existing calculate_streak() caller picks leave days up without any
    signature change. Returns an empty set if nobody is logged in or
    the lookup fails for any reason -- streaks then behave exactly as
    they did before leave days existed.
    """
    try:
        from auth.session import current_user_id
        from database.queries import get_leave_dates

        return get_leave_dates(current_user_id())
    except Exception:
        return set()


def calculate_streak(active_dates: pd.Series, excused_dates=None) -> tuple[int, int]:
    """
    Given a Series/iterable of dates (any date-like values) on which the
    user was active, return (current_streak, longest_streak) in days.

    current_streak counts consecutive active days ending today or
    yesterday (so a streak isn't broken just because today hasn't
    happened yet). longest_streak is the best run anywhere in the data.

    excused_dates are leave days: they never break a streak (a run of
    active days continues straight across them) but they don't add to
    the count either, like a "streak freeze". If not given, the
    logged-in user's leave days are used.
    """
    if active_dates is None or len(active_dates) == 0:
        return 0, 0

    if excused_dates is None:
        excused_dates = load_leave_dates()
    excused = {pd.Timestamp(d).date() for d in excused_dates}

    unique_days = sorted({pd.Timestamp(d).date() for d in active_dates})
    day_set = set(unique_days)

    def _bridged(prev, curr) -> bool:
        """True if every day strictly between prev and curr is a leave day."""
        gap = (curr - prev).days
        return all((prev + timedelta(days=i)) in excused for i in range(1, gap))

    # Longest streak: walk through sorted unique days.
    longest = 1
    running = 1
    for prev, curr in zip(unique_days, unique_days[1:]):
        if _bridged(prev, curr):  # consecutive, or only leave days in between
            running += 1
            longest = max(longest, running)
        else:
            running = 1

    # Current streak: count backwards from today (or yesterday).
    today = date.today()
    cursor = today
    if today not in day_set and today not in excused:
        cursor = today - timedelta(days=1)  # today isn't over yet

    current = 0
    while True:
        if cursor in day_set:
            current += 1
        elif cursor not in excused:
            break
        cursor -= timedelta(days=1)

    return current, longest


def empty_state(icon: str, title: str, subtitle: str) -> str:
    """Return a small markdown block for a consistent empty-state message."""
    return f"### {icon} {title}\n\n{subtitle}"


def get_daily_quote(custom_quote: str | None = None) -> tuple[str, str | None]:
    """
    Returns (text, author) to show on the Dashboard. If the user has
    set their own custom_quote (Settings), that's always used (author
    is None -- it's their own line). Otherwise picks one real, quoted
    line from config.constants.DAILY_MOTIVATION deterministically by
    today's date -- same quote for everyone that day, a different one
    tomorrow, no randomness/state needed.
    """
    if custom_quote and custom_quote.strip():
        return custom_quote.strip(), None

    from config.constants import DAILY_MOTIVATION

    index = date.today().toordinal() % len(DAILY_MOTIVATION)
    return DAILY_MOTIVATION[index]
