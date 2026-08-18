"""
auth/session.py

Thin wrapper around st.session_state for tracking who's logged in.
This is the ONLY place in the app that should read/write the
"user_*" session_state keys directly -- every page imports these
helpers instead of touching st.session_state itself.

Note: st.session_state only persists for the current browser tab
session (it resets on a hard refresh / new browser session). Full
"remember me across browser restarts" would need browser cookies,
which is a future enhancement, not part of v0.1.
"""

import streamlit as st


def login(user: dict) -> None:
    """Store the authenticated user in session state."""
    st.session_state["user_id"] = user["id"]
    st.session_state["user_name"] = user["name"]
    st.session_state["user_email"] = user["email"]


def logout() -> None:
    for key in ("user_id", "user_name", "user_email", "snapshots_ensured_date", "goal_maintenance_date"):
        st.session_state.pop(key, None)


def is_logged_in() -> bool:
    return st.session_state.get("user_id") is not None


def current_user_id() -> int:
    return st.session_state["user_id"]


def current_user_name() -> str:
    return st.session_state.get("user_name", "")


def current_user_email() -> str:
    return st.session_state.get("user_email", "")


def require_login() -> None:
    """
    Call at the top of every page (except the main login/signup page).
    Stops rendering and prompts the user to log in if there's no
    active session. Also runs two once-per-day-per-session
    maintenance checks:

    - Refreshes this user's weekly/monthly/yearly snapshots for the
      CURRENT period (analytics.snapshot.ensure_current_snapshots) --
      see that module for why an on-visit refresh is how "automatic"
      snapshots work in an app with no background scheduler.
    - Auto-shifts any goal whose schedule fell behind (a task's date
      passed without being marked done) and shows a toast for any
      goal that starts today (analytics.goal_maintenance).
    """
    if not is_logged_in():
        st.warning("Please log in to view this page.")
        st.info("Head back to the **LifeOS** main page to log in or create an account.")
        st.stop()

    from datetime import date

    today_str = date.today().isoformat()
    if st.session_state.get("snapshots_ensured_date") != today_str:
        from analytics.snapshot import ensure_current_snapshots

        try:
            ensure_current_snapshots(current_user_id())
        except Exception:
            # Snapshot refresh is a nice-to-have -- never let it block
            # the actual page the user came here for.
            pass
        st.session_state["snapshots_ensured_date"] = today_str

    if st.session_state.get("goal_maintenance_date") != today_str:
        from analytics.goal_maintenance import auto_shift_overdue_tasks, get_goals_starting_today

        try:
            shifted = auto_shift_overdue_tasks(current_user_id())
            for item in shifted:
                st.toast(
                    f"⏳ '{item['goal_title']}' had a missed task -- its whole schedule moved "
                    f"forward {item['shift_days']} day(s). New end date: {item['new_end_date']}.",
                    icon="⏳",
                )

            starting = get_goals_starting_today(current_user_id())
            for goal in starting:
                st.toast(f"🚀 '{goal['title']}' starts today!", icon="🚀")
        except Exception:
            # Same reasoning as above -- this is a nice-to-have, never
            # let it block the page the user actually came here for.
            pass
        st.session_state["goal_maintenance_date"] = today_str
