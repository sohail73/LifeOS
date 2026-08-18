"""
pages/3_Coding_Tracker.py

Coding problem tracker: manual entry (product spec section 15) plus
an optional semi-automatic LeetCode sync (section 23-style hybrid
approach). Sync pulls recent accepted submissions from LeetCode's
public profile data, but always stages them for the user to confirm
before saving -- manual entry remains the permanent fallback.
"""

from datetime import date

import streamlit as st

from auth.session import current_user_id, current_user_name, require_login
from config.constants import CODING_PLATFORMS, CODING_TOPICS, DIFFICULTY_LEVELS
from database.queries import (
    add_coding_log,
    add_language,
    ensure_default_languages,
    get_coding_logs_df,
    get_languages,
    get_leetcode_username,
    get_synced_external_ids,
    set_leetcode_username,
)
from integrations.leetcode_sync import LeetCodeSyncError, preview_new_submissions
from database.queries import get_avatar_base64
from utils.ui import difficulty_badge, duration_input, render_sidebar_branding

st.set_page_config(page_title="Coding Tracker - LifeOS", page_icon="⚡", layout="wide")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
st.title("Coding Tracker")

ensure_default_languages(user_id)
languages = get_languages(user_id)
language_names = [l["name"] for l in languages]

entry_tab, sync_tab, history_tab = st.tabs(["Log a Problem", "LeetCode Sync", "History"])

with entry_tab:
    st.subheader("Log a Solved Problem")

    with st.expander("Add a new language"):
        with st.form("add_language_form"):
            new_lang = st.text_input("Language name", placeholder="e.g. Pandas, Scala, R")
            add_lang_submitted = st.form_submit_button("Add Language")
        if add_lang_submitted:
            if not new_lang.strip():
                st.error("Language name can't be empty.")
            else:
                add_language(user_id, new_lang)
                st.success(f"Added '{new_lang.strip()}' -- it'll show up in the dropdown below now.")
                st.rerun()

    with st.form("coding_log_form"):
        col1, col2 = st.columns(2)
        with col1:
            platform = st.selectbox("Platform", CODING_PLATFORMS)
            problem_name = st.text_input("Problem Name", placeholder="e.g. Two Sum")
            language = st.selectbox("Language", language_names)
            difficulty = st.selectbox("Difficulty", DIFFICULTY_LEVELS)
        with col2:
            topic = st.selectbox("Topic", CODING_TOPICS)
            date_solved = st.date_input("Date Solved", value=date.today(), max_value=date.today())
            notes = st.text_area("Notes (optional)")

        time_taken = duration_input("Time Taken", key="coding_time_taken", default_minutes=20, max_hours=10)

        submitted = st.form_submit_button("Save Problem", use_container_width=True)

    if submitted:
        if not problem_name.strip():
            st.error("Problem name is required.")
        else:
            add_coding_log(
                user_id=user_id,
                platform=platform,
                problem_name=problem_name,
                language=language,
                difficulty=difficulty,
                topic=topic,
                date_solved=date_solved.isoformat(),
                time_taken_minutes=time_taken or None,
                notes=notes,
            )
            st.success(f"Logged '{problem_name}' ({difficulty}, {language}).")

with sync_tab:
    st.subheader("Sync with LeetCode")
    st.caption(
        "Pulls your recent **accepted** submissions from your public LeetCode profile. "
        "This uses LeetCode's undocumented public data (there's no official API), so it "
        "requires your profile to be public and needs a manual 'Sync Now' click each time -- "
        "there's no real-time push. You'll review and confirm before anything is saved."
    )

    current_username = get_leetcode_username(user_id) or ""
    username_input = st.text_input("Your LeetCode username", value=current_username)
    if username_input != current_username:
        set_leetcode_username(user_id, username_input)

    if st.button("🔄 Sync Now", use_container_width=True, disabled=not username_input.strip()):
        already_synced = get_synced_external_ids(user_id)
        with st.spinner("Fetching recent submissions from LeetCode..."):
            try:
                pending = preview_new_submissions(username_input, already_synced, limit=20)
                st.session_state["leetcode_pending_sync"] = pending
                if not pending:
                    st.info("No new solved problems found (or everything found is already logged).")
            except LeetCodeSyncError as e:
                st.error(f"Sync failed: {e}")

    pending = st.session_state.get("leetcode_pending_sync") or []
    if pending:
        st.write(f"**{len(pending)} new problem(s) found.** Confirm the language for each, then save.")

        with st.form("confirm_sync_form"):
            languages_chosen = {}
            for index, item in enumerate(pending):
                cols = st.columns([3, 2, 2, 2])
                cols[0].write(f"**{item['title']}**")
                cols[1].markdown(difficulty_badge(item["difficulty"]), unsafe_allow_html=True)
                cols[2].caption(item["topic"])
                languages_chosen[item["titleSlug"]] = cols[3].selectbox(
                    "Language", language_names, key=f"lang_{index}_{item['titleSlug']}",
                    label_visibility="collapsed",
                )
            save_all = st.form_submit_button("💾 Save All", use_container_width=True)

        if save_all:
            saved_count = 0
            for item in pending:
                result = add_coding_log(
                    user_id=user_id,
                    platform="LeetCode",
                    problem_name=item["title"],
                    language=languages_chosen[item["titleSlug"]],
                    difficulty=item["difficulty"],
                    topic=item["topic"],
                    date_solved=item["date_solved"],
                    source="leetcode",
                    external_id=item["titleSlug"],
                )
                if result is not None:
                    saved_count += 1
            del st.session_state["leetcode_pending_sync"]
            st.success(f"Saved {saved_count} problem(s) from LeetCode.")
            st.rerun()

with history_tab:
    st.subheader("Recent Problems")
    df = get_coding_logs_df(user_id)

    if df.empty:
        st.info(
            "**No coding activity yet.**\n\n"
            "Add your first solved problem in the **Log a Problem** tab, "
            "or sync it in from LeetCode."
        )
    else:
        display_df = df.sort_values("date_solved", ascending=False).copy()
        display_df["date_solved"] = display_df["date_solved"].dt.strftime("%d %b %Y")
        display_df = display_df[
            ["date_solved", "problem_name", "platform", "language", "difficulty", "topic",
             "time_taken_minutes", "source"]
        ]
        display_df.columns = ["Date", "Problem", "Platform", "Language", "Difficulty", "Topic",
                               "Time (min)", "Source"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
