"""
pages/4_Analytics.py

The deep-dive analytics page. Every chart here answers a specific
question (per product spec section 1, principle 7) rather than
being a chart for its own sake.
"""

import streamlit as st

from analytics import coding_analytics as ca
from analytics import study_analytics as sa
from auth.session import current_user_id, current_user_name, require_login
from database.queries import get_coding_logs_df, get_study_sessions_df
from utils.helper import format_duration
from widgets.charts import bar_chart, donut_chart, line_chart, multi_line_chart, study_heatmap
from database.queries import get_avatar_base64
from utils.ui import render_sidebar_branding

st.set_page_config(page_title="Analytics - LifeOS", page_icon="⚡", layout="wide")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
st.title("Analytics")

study_df = get_study_sessions_df(user_id)
coding_df = get_coding_logs_df(user_id)

if study_df.empty and coding_df.empty:
    st.info(
        "**No data yet.**\n\n"
        "Log a study session or a solved problem to unlock your analytics."
    )
    st.stop()

study_tab, coding_tab = st.tabs(["Study Analytics", "Coding Analytics"])

# ---------------------------------------------------------------------------
# Study analytics
# ---------------------------------------------------------------------------
with study_tab:
    if study_df.empty:
        st.info("No study data yet. Start your first study session to unlock this section.")
    else:
        st.subheader("How much have I studied, and when?")
        daily = sa.daily_totals(study_df, days=30)
        daily["hours"] = (daily["duration_minutes"] / 60).round(2)
        st.plotly_chart(
            line_chart(daily, "date", "hours", "Study Time -- Last 30 Days", "Hours"),
            use_container_width=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Where does my time go?")
            breakdown = sa.subject_breakdown(study_df)
            breakdown["hours"] = (breakdown["duration_minutes"] / 60).round(2)
            for _, row in breakdown.iterrows():
                st.write(f"**{row['subject']}**: {format_duration(row['duration_minutes'])}")
            st.plotly_chart(
                donut_chart(breakdown, "subject", "hours", "Time by Subject"),
                use_container_width=True,
            )

        with col2:
            st.subheader("Which days am I most productive?")
            weekday = sa.weekday_totals(study_df)
            weekday["avg_hours"] = (weekday["avg_minutes"] / 60).round(2)
            st.plotly_chart(
                bar_chart(weekday, "weekday", "avg_hours", "Average Study Hours by Weekday"),
                use_container_width=True,
            )

        st.subheader("Study consistency")
        heatmap_df = sa.heatmap_data(study_df, days=182)
        st.plotly_chart(study_heatmap(heatmap_df, "Study Activity -- Last 6 Months"), use_container_width=True)

        growth = sa.week_over_week_growth(study_df)
        if growth is not None:
            direction = "up" if growth >= 0 else "down"
            st.caption(f"Study time is {direction} {abs(growth)}% vs. last week.")

# ---------------------------------------------------------------------------
# Coding analytics
# ---------------------------------------------------------------------------
with coding_tab:
    if coding_df.empty:
        st.info("No coding activity yet. Add your first solved problem to unlock this section.")
    else:
        st.subheader("What am I coding, in which language?")
        trend = ca.language_trend(coding_df, days=60)
        if not trend.empty:
            st.plotly_chart(
                multi_line_chart(trend, "date", "count", "language", "Language Activity -- Last 60 Days"),
                use_container_width=True,
            )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Language Distribution**")
            lang_dist = ca.language_distribution(coding_df)
            st.plotly_chart(
                donut_chart(lang_dist, "language", "count", "By Language"), use_container_width=True
            )
        with col2:
            st.markdown("**Difficulty Distribution**")
            diff_dist = ca.difficulty_distribution(coding_df)
            st.plotly_chart(
                donut_chart(diff_dist, "difficulty", "count", "By Difficulty"), use_container_width=True
            )
        with col3:
            st.markdown("**Where am I strong or weak?**")
            topic_dist = ca.topic_distribution(coding_df)
            st.plotly_chart(
                bar_chart(topic_dist, "topic", "count", "By Topic", orientation="h"),
                use_container_width=True,
            )

        avg_time = ca.average_solving_time(coding_df)
        most_active = ca.most_active_weekday(coding_df)
        info_col1, info_col2 = st.columns(2)
        info_col1.metric("Average Solving Time", f"{avg_time:.0f} min" if avg_time else "N/A")
        info_col2.metric("Most Active Day", most_active or "N/A")
