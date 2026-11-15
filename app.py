"""
app.py

LifeOS entry point. Initializes the database, then either shows the
Login / Create Account screen (first-time or logged-out users) or a
short welcome-back screen that points to the sidebar pages.

All the real functionality (Dashboard, Study, Coding Tracker,
Analytics, AI Insights, Snapshots, Wrapped, Settings) lives in
pages/ and is reached through Streamlit's automatic sidebar
navigation once the user is logged in.
"""

import streamlit as st

from auth.auth_utils import authenticate_user, create_user
from auth.session import (
    current_user_id,
    current_user_name,
    flush_cookie_actions,
    is_logged_in,
    login,
    login_diag,
    logout,
    try_auto_login,
)
from database import cloud_backup
from database.create_tables import initialize_database
from database.queries import ensure_default_subjects, get_avatar_base64
from utils.ui import inject_global_css, page_header, render_sidebar_branding

st.set_page_config(page_title="LifeOS", page_icon="⚡", layout="wide")

initialize_database()


def render_login_form() -> None:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        remember = st.checkbox("Keep me logged in on this device (untick on a shared computer)", value=True)
        submitted = st.form_submit_button("Log In", use_container_width=True)

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
            return
        user = authenticate_user(email, password)
        if user is None:
            st.error("Incorrect email or password.")
            return
        login(user, remember=remember)
        st.success(f"Welcome back, {user['name']}!")
        st.rerun()


def render_signup_form() -> None:
    with st.form("signup_form"):
        name = st.text_input("Name")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create Account", use_container_width=True)

    if submitted:
        if not name or not email or not password:
            st.error("Please fill in every field.")
            return
        if len(password) < 8:
            st.error("Password must be at least 8 characters.")
            return
        if password != confirm:
            st.error("Passwords don't match.")
            return

        user_id = create_user(name, email, password)
        if user_id is None:
            st.error("An account with that email already exists.")
            return

        ensure_default_subjects(user_id)
        user = {"id": user_id, "name": name.strip(), "email": email.strip().lower()}
        login(user, remember=True)
        st.success("Account created! Setting up your workspace...")
        st.rerun()


def render_logged_out_view() -> None:
    inject_global_css()

    backup_status = cloud_backup.status()
    if not backup_status["enabled"]:
        server_line = "Cloud backup: OFF (secrets not found on this server)"
    elif backup_status["blocked"]:
        server_line = "Cloud backup: ON, but restore FAILED"
    elif backup_status["restored"]:
        server_line = "Cloud backup: ON, data restored from your backup"
    elif backup_status["checked"]:
        server_line = "Cloud backup: ON, no restore needed (this server's data is already in sync)"
    else:
        server_line = "Cloud backup: ON, startup check has not finished"
    st.caption(
        f"Server status -- {server_line} -- accounts on this server: {backup_status['accounts']}"
        f" -- saved login: {login_diag()}"
    )
    if backup_status["blocked"]:
        st.error(
            "Your saved data could not be restored right now, so please do NOT create a new account "
            "or add data yet. Refresh this page in a minute. "
            f"Details: {backup_status['last_error']}"
        )

    hero_col, form_col = st.columns([1.25, 1], gap="large")

    with hero_col:
        st.markdown(
            '<div class="lifeos-pill"><span class="dot"></span>Your personal OS</div>'
            '<div class="lifeos-hero-title">Life<span class="lifeos-hl">OS</span></div>'
            '<div class="lifeos-hero-sub">Track. Analyze. Improve.</div>'
            '<div class="lifeos-checks">'
            '<div class="lifeos-check"><span class="tick">&#10003;</span>Study timer with daily streaks</div>'
            '<div class="lifeos-check"><span class="tick">&#10003;</span>Coding tracker and analytics</div>'
            '<div class="lifeos-check"><span class="tick">&#10003;</span>Goals, tasks and priorities</div>'
            '<div class="lifeos-check"><span class="tick">&#10003;</span>Career roadmap and countdown</div>'
            '<div class="lifeos-check"><span class="tick">&#10003;</span>Gym log and weekly progress</div>'
            '<div class="lifeos-check"><span class="tick">&#10003;</span>Weekly AI insights and recaps</div>'
            '</div>'
            '<p style="margin-top:28px;color:#3B4052;max-width:34rem;">'
            '<span style="color:#F5A623;letter-spacing:2px;">&#9733;&#9733;&#9733;&#9733;&#9733;</span>&nbsp; '
            'LifeOS turns your study and coding activity into real analytics, insights, and progress '
            'reports -- automatically, and your data stays in your own database.</p>',
            unsafe_allow_html=True,
        )

    with form_col:
        login_tab, signup_tab = st.tabs(["Login", "Create Account"])
        with login_tab:
            render_login_form()
        with signup_tab:
            render_signup_form()


def render_logged_in_view() -> None:
    render_sidebar_branding(current_user_name(), get_avatar_base64(current_user_id()))
    page_header(
        f"Welcome back, {current_user_name()}",
        subtitle="Pick up right where you left off.",
        eyebrow="LifeOS",
    )
    st.write(
        "Use the sidebar to jump into your **Dashboard**, log a **Study** "
        "session, track a **Coding** problem, plan your **Goals & Tasks**, dig into "
        "**Analytics**, read your **AI Insights**, browse **Snapshots**, or check your **Wrapped**."
    )

    if st.button("Log Out"):
        logout()
        st.rerun()


flush_cookie_actions()
try_auto_login()

if is_logged_in():
    render_logged_in_view()
else:
    render_logged_out_view()
