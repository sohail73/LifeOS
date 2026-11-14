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
from database import cloud_backup
from database.backup_tools import is_owner, make_backup_bytes, restore_from_bytes, validate_backup
from database.create_tables import initialize_database
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

# ---------------------------------------------------------------------------
# Backup & Restore -- owner only (the database holds every account's data)
# ---------------------------------------------------------------------------
if is_owner(user_id, current_user_email()):
    st.subheader("Backup & Restore")
    st.caption(
        "Download a copy of the whole LifeOS database (all accounts) and keep it somewhere safe. "
        "If the hosted app ever resets, you can restore from it here."
    )

    from datetime import datetime

    cloud = cloud_backup.status()
    if cloud["enabled"]:
        if cloud["blocked"]:
            st.error(f"Automatic cloud backup is PAUSED. {cloud['last_error']}")
        elif cloud["last_error"]:
            st.warning(cloud["last_error"])
        elif cloud["last_backup"]:
            st.success(
                "Automatic cloud backup is ON. Last backup: "
                + cloud["last_backup"].strftime("%d %b %Y, %H:%M UTC")
            )
        else:
            st.info("Automatic cloud backup is ON. It runs about 30 seconds after your next change.")
        if st.button("Back up to cloud now", use_container_width=True):
            done, done_msg = cloud_backup.backup_now()
            (st.success if done else st.error)(done_msg)
    else:
        st.caption("Automatic cloud backup is off (not configured on this server).")

    st.download_button(
        "Download backup (.db)",
        data=make_backup_bytes(),
        file_name=f"lifeos_backup_{datetime.now().strftime('%Y-%m-%d_%H%M')}.db",
        mime="application/octet-stream",
        use_container_width=True,
    )

    with st.expander("Restore from a backup file"):
        st.warning(
            "This replaces ALL current data (every account) with the contents of the backup. "
            "A safety copy of the current data is kept on the server first."
        )
        backup_file = st.file_uploader("Backup file (.db)", type=["db"], key="restore_uploader")
        if backup_file is not None:
            backup_bytes = backup_file.getvalue()
            valid, valid_msg = validate_backup(backup_bytes)
            if valid:
                st.info(valid_msg)
            else:
                st.error(valid_msg)

            if valid:
                restore_confirm = st.checkbox("I understand this replaces all current data.", key="restore_confirm")
                restore_password = st.text_input("Your password", type="password", key="restore_password")
                if st.button("Restore now", use_container_width=True):
                    if not restore_confirm:
                        st.error("Please check the confirmation box.")
                    elif authenticate_user(current_user_email(), restore_password) is None:
                        st.error("Incorrect password. Nothing was changed.")
                    else:
                        done, done_msg = restore_from_bytes(backup_bytes)
                        if done:
                            initialize_database()  # apply migrations if the backup is from an older version
                            st.success(done_msg + " Please log in again.")
                            logout()
                            st.rerun()
                        else:
                            st.error(done_msg)

if st.button("Log Out"):
    logout()
    st.rerun()
