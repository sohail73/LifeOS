"""
auth/session.py

Thin wrapper around st.session_state for tracking who's logged in.
This is the ONLY place in the app that should read/write the
"user_*" session_state keys directly -- every page imports these
helpers instead of touching st.session_state itself.

st.session_state alone is wiped when the browser tab is closed, so
"Keep me logged in" adds a browser cookie holding a random token
(see auth/remember_tokens.py). Next visit, try_auto_login() reads the
cookie and logs you straight in. Cookies are written by a tiny script
(flush_cookie_actions) on the page render AFTER login/logout.
"""

import streamlit as st

from auth import remember_tokens
from config import timezone as _timezone  # noqa: F401  (sets the app to IST on import)

COOKIE_NAME = "lifeos_session"


def _cookie_token():
    """The login token the browser sent when this session started (None if none/unsupported)."""
    try:
        return st.context.cookies.get(COOKIE_NAME)
    except Exception:
        return None


def login(user: dict, remember: bool = False) -> None:
    """Store the authenticated user in session state. With remember=True this
    device also stays logged in (cookie) for TOKEN_DAYS days."""
    st.session_state["user_id"] = user["id"]
    st.session_state["user_name"] = user["name"]
    st.session_state["user_email"] = user["email"]
    st.session_state["_auto_login_tried"] = True

    if remember:
        try:
            token = remember_tokens.create_token(user["id"])
            st.session_state["_remember_token"] = token
            st.session_state["_cookie_action"] = ("set", token)
        except Exception:
            pass  # remembering is a convenience; never block a normal login


def try_auto_login() -> None:
    """If this browser has a valid "keep me logged in" cookie, log in without a password.
    Tries once per session. Never writes to the database."""
    if is_logged_in() or st.session_state.get("_auto_login_tried"):
        return
    st.session_state["_auto_login_tried"] = True
    try:
        user = remember_tokens.user_for_token(_cookie_token())
    except Exception:
        user = None
    if user is not None:
        st.session_state["user_id"] = user["id"]
        st.session_state["user_name"] = user["name"]
        st.session_state["user_email"] = user["email"]


def flush_cookie_actions() -> None:
    """Writes/clears the browser cookie requested by login()/logout(). Call near the top of every page."""
    action = st.session_state.pop("_cookie_action", None)
    if not action:
        return
    kind, token = action
    max_age = 60 * 60 * 24 * remember_tokens.TOKEN_DAYS if kind == "set" else 0
    value = token if kind == "set" else ""
    script = (
        "<script>(function(){"
        "var p=window.parent;"
        "var secure=(p.location.protocol==='https:')?'; Secure':'';"
        f"p.document.cookie='{COOKIE_NAME}={value}; max-age={max_age}; path=/; SameSite=Lax'+secure;"
        "})();</script>"
    )
    try:
        import streamlit.components.v1 as components

        components.html(script, height=0)
    except Exception:
        pass


def logout() -> None:
    """Log out and make this device forget the login (token deleted + cookie cleared)."""
    for raw in {st.session_state.get("_remember_token"), _cookie_token()}:
        try:
            remember_tokens.delete_token(raw)
        except Exception:
            pass
    for key in (
        "user_id", "user_name", "user_email", "snapshots_ensured_date",
        "goal_maintenance_date", "_remember_token",
    ):
        st.session_state.pop(key, None)
    st.session_state["_cookie_action"] = ("clear", None)
    st.session_state["_auto_login_tried"] = True  # don't auto-login again in this session


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
    flush_cookie_actions()
    try_auto_login()

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
