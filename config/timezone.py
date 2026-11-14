"""
config/timezone.py

Makes the whole app think in Indian Standard Time (IST, UTC+5:30).

Why: on your own PC the clock is already IST, so "today" flips at 12:00 AM.
Streamlit Cloud servers run on UTC, so there "today" flipped at 5:30 AM IST
and Today's Tasks, streaks, goals etc. looked a day behind after midnight.

Every `date.today()` / `datetime.now()` in the app follows the process
timezone, so setting it once here fixes all of them. IST has no daylight
saving, so the fixed POSIX string "IST-5:30" is exact and needs no timezone
database. To use another timezone set APP_TIMEZONE (e.g. "Asia/Dubai" or a
POSIX string) as an environment variable.

Windows has no tzset(); there the PC's own timezone is used (already IST).
"""

import os
import time


def apply_app_timezone() -> None:
    if not hasattr(time, "tzset"):
        return
    os.environ["TZ"] = os.environ.get("APP_TIMEZONE") or "IST-5:30"
    time.tzset()


apply_app_timezone()
