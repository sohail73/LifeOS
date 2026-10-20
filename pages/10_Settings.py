"""
pages/9_Settings.py

Simple settings: profile picture, daily goals (used across the
Dashboard and Snapshots' goal-completion calculation), a
password-protected full data reset, and account actions. Widget
enable/disable and layout customization (product spec section 37)
are a future enhancement, not part of v0.1.
"""

import base64

import streamlit as st

from auth.auth_utils import authenticate_user, change_password
from auth.session import current_user_email, current_user_id, current_user_name, logout, require_login
from database.queries import get_custom_quote, get_goals, reset_user_data, set_avatar_base64, set_custom_quote, update_goals
from database.queries import get_avatar_base64
from utils.ui import page_header, avatar_img_tag, duration_input, render_sidebar_branding

st.set_page_config(page_title="Settings - LifeOS", page_icon="⚙️", layout="centered")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
page_header("Settings", eyebrow="Preferences")

st.subheader("Profile")
st.write(f"**Name:** {current_user_name()}")

current_avatar = get_avatar_base64(user_id)
if current_avatar:
    st.markdown(avatar_img_tag(current_avatar, size=80), unsafe_allow_html=True)

uploaded_avatar = st.file_uploader("Profile picture (optional)", type=["png", "jpg", "jpeg"])
avatar_col1, avatar_col2 = st.columns(2)

if uploaded_avatar is not None:
    if avatar_col1.button("Save Picture", use_container_width=True):
        encoded = base64.b64encode(uploaded_avatar.read()).decode("utf-8")
        set_avatar_base64(user_id, encoded)
        st.success("Profile picture updated.")
        st.rerun()

if current_avatar:
    if avatar_col2.button("Remove Picture", use_container_width=True):
        set_avatar_base64(user_id, None)
        st.success("Profile picture removed.")
        st.rerun()

st.divider()

st.subheader("Daily Goals")
st.caption("These drive your goal-completion percentage on the Dashboard and Snapshots.")

goals = get_goals(user_id)

with st.form("goals_form"):
    study_goal_minutes = duration_input(
        "Daily study goal", key="daily_study_goal", default_minutes=goals["daily_study_minutes_goal"]
    )
    problems_goal = st.number_input(
        "Daily problems goal",
        min_value=1,
        max_value=50,
        value=goals["daily_problems_goal"],
    )
    submitted = st.form_submit_button("Save Goals", use_container_width=True)

if submitted:
    update_goals(user_id, int(study_goal_minutes), int(problems_goal))
    st.success("Goals updated.")
    st.rerun()

st.divider()

st.subheader("Daily Motivation")
st.caption(
    "By default, a new real quote shows on your Dashboard each day, automatically. "
    "Set your own line here if you'd rather always see the same one."
)

current_custom_quote = get_custom_quote(user_id) or ""
with st.form("custom_quote_form"):
    quote_input = st.text_input(
        "Your own quote (leave empty to go back to automatic daily quotes)",
        value=current_custom_quote,
        placeholder="e.g. Keep going, you're closer than you think.",
    )
    quote_submitted = st.form_submit_button("Save", use_container_width=True)

if quote_submitted:
    set_custom_quote(user_id, quote_input)
    if quote_input.strip():
        st.success("Your custom quote is now set.")
    else:
        st.success("Cleared -- back to automatic daily quotes.")
    st.rerun()

st.divider()

st.subheader("Change Password")
with st.form("change_password_form"):
    current_password = st.text_input("Current password", type="password")
    new_password = st.text_input("New password", type="password")
    confirm_new_password = st.text_input("Confirm new password", type="password")
    change_pw_submitted = st.form_submit_button("Update Password", use_container_width=True)

if change_pw_submitted:
    if not current_password or not new_password:
        st.error("Fill in every field.")
    elif len(new_password) < 8:
        st.error("New password must be at least 8 characters.")
    elif new_password != confirm_new_password:
        st.error("New passwords don't match.")
    else:
        success = change_password(user_id, current_user_email(), current_password, new_password)
        if success:
            st.success("Password updated.")
        else:
            st.error("Current password is incorrect. Nothing was changed.")

st.divider()

st.subheader("Reset All Data")
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
