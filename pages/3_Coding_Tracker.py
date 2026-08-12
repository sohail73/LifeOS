"""
pages/3_Coding_Tracker.py

Coding problem tracker (manual mode -- see product spec section 15).
Automatic sync (e.g. a LeetCode API) is intentionally not built here
since no reliable public API was verified; manual entry always
remains available as the fallback either way.
"""

from datetime import date

import streamlit as st

from auth.session import current_user_id, require_login
from config.constants import CODING_LANGUAGES, CODING_PLATFORMS, CODING_TOPICS, DIFFICULTY_LEVELS
from database.queries import add_coding_log, get_coding_logs_df

st.set_page_config(page_title="Coding Tracker - LifeOS", page_icon="🧩", layout="wide")
require_login()

user_id = current_user_id()
st.title("Coding Tracker")

entry_tab, history_tab = st.tabs(["Log a Problem", "History"])

with entry_tab:
    st.subheader("Log a Solved Problem")

    with st.form("coding_log_form"):
        col1, col2 = st.columns(2)
        with col1:
            platform = st.selectbox("Platform", CODING_PLATFORMS)
            problem_name = st.text_input("Problem Name", placeholder="e.g. Two Sum")
            language = st.selectbox("Language", CODING_LANGUAGES)
            difficulty = st.selectbox("Difficulty", DIFFICULTY_LEVELS)
        with col2:
            topic = st.selectbox("Topic", CODING_TOPICS)
            date_solved = st.date_input("Date Solved", value=date.today(), max_value=date.today())
            time_taken = st.number_input("Time Taken (minutes)", min_value=0, max_value=600, value=20)
            notes = st.text_area("Notes (optional)")

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

with history_tab:
    st.subheader("Recent Problems")
    df = get_coding_logs_df(user_id)

    if df.empty:
        st.info(
            "**No coding activity yet.**\n\n"
            "Add your first solved problem in the **Log a Problem** tab."
        )
    else:
        display_df = df.sort_values("date_solved", ascending=False).copy()
        display_df["date_solved"] = display_df["date_solved"].dt.strftime("%d %b %Y")
        display_df = display_df[
            ["date_solved", "problem_name", "platform", "language", "difficulty", "topic", "time_taken_minutes"]
        ]
        display_df.columns = ["Date", "Problem", "Platform", "Language", "Difficulty", "Topic", "Time (min)"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
