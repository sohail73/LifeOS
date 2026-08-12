"""
pages/8_Settings.py

Simple settings: daily goals (used across the Dashboard and
Snapshots' goal-completion calculation), a password-protected full
data reset, and account actions. Widget enable/disable and layout
customization (product spec section 37) are a future enhancement,
not part of v0.1.
"""

import streamlit as st

from auth.auth_utils import authenticate_user
from auth.session import current_user_email, current_user_id, current_user_name, logout, require_login
from database.queries import get_goals, reset_user_data, update_goals

st.set_page_config(page_title="Settings - LifeOS", page_icon="⚙️", layout="centered")
require_login()

user_id = current_user_id()
st.title("Settings")

st.subheader("Profile")
st.write(f"**Name:** {current_user_name()}")

st.divider()

st.subheader("Daily Goals")
st.caption("These drive your goal-completion percentage on the Dashboard and Snapshots.")

goals = get_goals(user_id)

with st.form("goals_form"):
    study_goal = st.number_input(
        "Daily study goal (minutes)",
        min_value=5,
        max_value=1440,
        value=goals["daily_study_minutes_goal"],
        step=5,
    )
    problems_goal = st.number_input(
        "Daily problems goal",
        min_value=1,
        max_value=50,
        value=goals["daily_problems_goal"],
    )
    submitted = st.form_submit_button("Save Goals", use_container_width=True)

if submitted:
    update_goals(user_id, int(study_goal), int(problems_goal))
    st.success("Goals updated.")
    st.rerun()

st.divider()

st.subheader("⚠️ Reset All Data")
st.caption(
    "Permanently deletes every study session, coding log, task, goal, and snapshot on "
    "this account, and resets your daily goals to default. Your login (name/email/password) "
    "stays the same -- this puts your account back to a fresh, just-signed-up state."
)

with st.expander("Reset my account data"):
    with st.form("reset_data_form"):
        confirm_password = st.text_input(
            "Enter your password to confirm", type="password", key="reset_password"
        )
        confirm_checkbox = st.checkbox("I understand this cannot be undone.")
        reset_submitted = st.form_submit_button("Reset Everything", use_container_width=True)

    if reset_submitted:
        if not confirm_password:
            st.error("Enter your password to confirm.")
        elif not confirm_checkbox:
            st.error("Please check the confirmation box.")
        else:
            user = authenticate_user(current_user_email(), confirm_password)
            if user is None:
                st.error("Incorrect password. Data was NOT reset.")
            else:
                reset_user_data(user_id)
                st.success("Your account has been reset. Redirecting...")
                st.rerun()

st.divider()

if st.button("Log Out"):
    logout()
    st.rerun()
