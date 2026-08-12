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
    for key in ("user_id", "user_name", "user_email"):
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
    active session.
    """
    if not is_logged_in():
        st.warning("Please log in to view this page.")
        st.info("Head back to the **LifeOS** main page to log in or create an account.")
        st.stop()
