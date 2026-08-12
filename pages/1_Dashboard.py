"""
pages/1_Dashboard.py

High-level Study dashboard: today's numbers, streaks, goal
completion, weekly/monthly totals, and recent activity. Deliberately
NOT every possible chart -- deep analytics live on the Analytics page.
"""

from datetime import date, timedelta

import streamlit as st

from analytics import coding_analytics as ca
from analytics import study_analytics as sa
from auth.session import current_user_name, require_login, current_user_id
from database.queries import get_coding_logs_df, get_goals, get_study_sessions_df
from utils.helper import format_duration

st.set_page_config(page_title="Dashboard - LifeOS", page_icon="📊", layout="wide")
require_login()

user_id = current_user_id()
st.title("Dashboard")
st.caption(f"Here's where things stand today, {current_user_name()}.")

study_df = get_study_sessions_df(user_id)
coding_df = get_coding_logs_df(user_id)
goals = get_goals(user_id)

today = date.today()
today_minutes = sa.minutes_on_date(study_df, today)
today_problems = ca.problems_on_date(coding_df, today)
current_streak, longest_streak = sa.get_streaks(study_df)

study_goal = goals["daily_study_minutes_goal"]
problems_goal = goals["daily_problems_goal"]
study_goal_pct = min(today_minutes / study_goal, 1.0) if study_goal else 0.0
problems_goal_pct = min(today_problems / problems_goal, 1.0) if problems_goal else 0.0
overall_goal_pct = round((study_goal_pct + problems_goal_pct) / 2 * 100, 1)

if study_df.empty and coding_df.empty:
    st.info(
        "**No activity yet.**\n\n"
        "Start your first study session or log a solved problem to unlock your dashboard."
    )
else:
    # --- Top row: today's snapshot ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Today's Study Time", format_duration(today_minutes))
    col2.metric("Problems Solved Today", today_problems)
    col3.metric("Current Streak", f"{current_streak} days")
    col4.metric("Longest Streak", f"{longest_streak} days")

    st.progress(overall_goal_pct / 100, text=f"Today's goal completion: {overall_goal_pct}%")

    st.divider()

    # --- Second row: weekly / monthly totals ---
    week_start = today - timedelta(days=6)
    month_start = today.replace(day=1)

    week_minutes = sa.minutes_since(study_df, week_start)
    month_minutes = sa.minutes_since(study_df, month_start)
    week_problems = ca.problems_since(coding_df, week_start)
    month_problems = ca.problems_since(coding_df, month_start)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("This Week's Study Time", format_duration(week_minutes))
    col2.metric("This Month's Study Time", format_duration(month_minutes))
    col3.metric("Problems This Week", week_problems)
    col4.metric("Problems This Month", month_problems)

    st.divider()

    # --- Recent activity ---
    st.subheader("Recent Activity")
    recent_col1, recent_col2 = st.columns(2)

    with recent_col1:
        st.markdown("**Latest Study Sessions**")
        if study_df.empty:
            st.caption("No study sessions logged yet.")
        else:
            recent_study = study_df.sort_values("date", ascending=False).head(5)
            for _, row in recent_study.iterrows():
                st.write(
                    f"- {row['date'].strftime('%d %b')} · **{row['subject']}** · "
                    f"{format_duration(row['duration_minutes'])}"
                )

    with recent_col2:
        st.markdown("**Latest Problems Solved**")
        if coding_df.empty:
            st.caption("No coding activity yet.")
        else:
            recent_coding = coding_df.sort_values("date_solved", ascending=False).head(5)
            for _, row in recent_coding.iterrows():
                st.write(
                    f"- {row['date_solved'].strftime('%d %b')} · **{row['problem_name']}** "
                    f"({row['difficulty']}, {row['language']})"
                )
