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
from auth.session import current_user_id, current_user_name, is_logged_in, login, logout
from database.create_tables import initialize_database
from database.queries import ensure_default_subjects, get_avatar_base64
from utils.ui import render_sidebar_branding

st.set_page_config(page_title="LifeOS", page_icon="⚡", layout="centered")

initialize_database()


def render_login_form() -> None:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In", use_container_width=True)

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
            return
        user = authenticate_user(email, password)
        if user is None:
            st.error("Incorrect email or password.")
            return
        login(user)
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
        login(user)
        st.success("Account created! Setting up your workspace...")
        st.rerun()


def render_logged_out_view() -> None:
    st.title("Welcome to LifeOS")
    st.subheader("Track. Analyze. Improve.")
    st.write(
        "LifeOS turns your study and coding activity into real analytics, "
        "insights, and progress reports -- automatically."
    )

    login_tab, signup_tab = st.tabs(["Login", "Create Account"])
    with login_tab:
        render_login_form()
    with signup_tab:
        render_signup_form()


def render_logged_in_view() -> None:
    render_sidebar_branding(current_user_name(), get_avatar_base64(current_user_id()))
    st.title("LifeOS")
    st.subheader(f"Welcome back, {current_user_name()}!")
    st.write(
        "Use the sidebar to jump into your **Dashboard**, log a **Study** "
        "session, track a **Coding** problem, plan your **Goals & Tasks**, dig into "
        "**Analytics**, read your **AI Insights**, browse **Snapshots**, or check your **Wrapped**."
    )

    if st.button("Log Out"):
        logout()
        st.rerun()


if is_logged_in():
    render_logged_in_view()
else:
    render_logged_out_view()
