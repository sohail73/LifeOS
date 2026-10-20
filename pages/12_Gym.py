"""
pages/12_Gym.py

A simple gym/workout tracker, in the same spirit as the Study and
Coding Tracker pages: log a workout (date, type, duration, notes),
see your current/longest streak, a GitHub-style activity heatmap of
workout days, and a breakdown of workout types -- plus a history list
you can delete entries from.
"""

from datetime import date

import streamlit as st

from analytics import gym_analytics as ga
from auth.session import current_user_id, current_user_name, require_login
from config.constants import WORKOUT_TYPES
from database.queries import (
    add_gym_session,
    delete_gym_session,
    get_avatar_base64,
    get_gym_sessions,
    get_gym_sessions_df,
)
from utils.helper import format_duration
from utils.ui import page_header, duration_input, kpi_card_row, render_sidebar_branding
from widgets.charts import donut_chart, gym_heatmap

st.set_page_config(page_title="Gym - LifeOS", page_icon="⚡", layout="wide")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
page_header("Gym", eyebrow="Training")
st.caption("Your workout log, streak, and activity at a glance.")

df = get_gym_sessions_df(user_id)

current_streak, longest_streak = ga.get_streaks(df)
total_sessions = ga.total_sessions(df)
total_hours = round(ga.total_minutes(df) / 60, 1)
sessions_this_week = ga.sessions_this_week(df)

kpi_card_row([
    {"icon": " ", "label": "Current Streak", "value": f"{current_streak}d", "sub": f"best {longest_streak}d", "color": "green"},
    {"icon": " ", "label": "Longest Streak", "value": f"{longest_streak}d", "color": "green"},
    {"icon": " ", "label": "Sessions This Week", "value": sessions_this_week},
    {"icon": " ", "label": "All-Time Sessions", "value": total_sessions},
    {"icon": " ", "label": "All-Time Hours", "value": f"{total_hours}h"},
])

log_tab, activity_tab, history_tab = st.tabs(["Log a Workout", "Activity", "History"])

# ---------------------------------------------------------------------------
# Log a workout
# ---------------------------------------------------------------------------
with log_tab:
    st.subheader("Log a Workout")
    with st.form("gym_log_form"):
        col1, col2 = st.columns(2)
        with col1:
            workout_type = st.selectbox("Workout Type", WORKOUT_TYPES)
            workout_date = st.date_input("Date", value=date.today(), max_value=date.today())
        with col2:
            duration = duration_input("Duration", key="gym_duration", default_minutes=60, max_hours=6)

        notes = st.text_area("Notes (optional)", placeholder="e.g. Bench 3x8 @ 60kg, OHP 3x10, Dips 3x12 -- felt strong")
        submitted = st.form_submit_button("Save Workout", use_container_width=True)

    if submitted:
        add_gym_session(
            user_id=user_id,
            date=workout_date.isoformat(),
            workout_type=workout_type,
            duration_minutes=duration or None,
            notes=notes,
        )
        st.success(f"Logged a {workout_type} workout on {workout_date.isoformat()}.")
        st.rerun()

# ---------------------------------------------------------------------------
# Activity -- heatmap + workout type breakdown
# ---------------------------------------------------------------------------
with activity_tab:
    if df.empty:
        st.info("No workouts logged yet. Add your first one in the **Log a Workout** tab.")
    else:
        st.subheader("Workout Activity")
        heatmap_df = ga.daily_counts(df, days=182)
        st.plotly_chart(gym_heatmap(heatmap_df, title="Gym Activity -- Last 6 Months"), use_container_width=True)

        st.subheader("Workout Type Breakdown")
        dist = ga.workout_type_distribution(df)
        if not dist.empty:
            st.plotly_chart(
                donut_chart(dist, names="workout_type", values="count", title="Sessions by Type"),
                use_container_width=True,
            )

# ---------------------------------------------------------------------------
# History -- recent sessions, deletable
# ---------------------------------------------------------------------------
with history_tab:
    st.subheader("Workout History")
    sessions = get_gym_sessions(user_id)

    if not sessions:
        st.info("No workouts logged yet.")
    else:
        for session in sessions:
            with st.container(border=True):
                date_col, type_col, duration_col, delete_col = st.columns([2, 2, 2, 1])
                date_col.write(session["date"])
                type_col.write(f"**{session['workout_type']}**")
                duration_col.write(format_duration(session["duration_minutes"]) if session["duration_minutes"] else "--")
                if delete_col.button("Delete", key=f"del_gym_{session['id']}"):
                    delete_gym_session(user_id, session["id"])
                    st.rerun()

                if session["notes"]:
                    st.caption(session["notes"])
