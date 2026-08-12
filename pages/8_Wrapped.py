"""
pages/7_Wrapped.py

Monthly and Yearly Wrapped -- a Spotify-Wrapped-style summary of the
user's period, generated live from study_sessions/coding_logs (see
analytics/wrapped.py).
"""

from datetime import date

import streamlit as st

from analytics.wrapped import monthly_wrapped, yearly_wrapped
from auth.session import current_user_id, require_login
from database.queries import get_coding_logs_df, get_study_sessions_df

st.set_page_config(page_title="Wrapped - LifeOS", page_icon="🎁", layout="wide")
require_login()

user_id = current_user_id()
st.title("Wrapped")

study_df = get_study_sessions_df(user_id)
coding_df = get_coding_logs_df(user_id)

today = date.today()
monthly_tab, yearly_tab = st.tabs(["Monthly Wrapped", "Yearly Wrapped"])

with monthly_tab:
    month_options = [
        (date(today.year, m, 1).strftime("%B %Y"), today.year, m) for m in range(1, today.month + 1)
    ]
    labels = [label for label, _, _ in month_options]
    selected = st.selectbox("Select month", labels, index=len(labels) - 1)
    _, sel_year, sel_month = month_options[labels.index(selected)]

    wrapped = monthly_wrapped(study_df, coding_df, sel_year, sel_month)

    if not wrapped["has_data"]:
        st.info(f"No activity recorded for {wrapped['period_label']} yet.")
    else:
        st.header(f" {wrapped['period_label'].upper()} WRAPPED")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Study Hours", wrapped["study_hours"])
        col2.metric("Problems Solved", wrapped["problems_solved"])
        col3.metric("Longest Streak", f"{wrapped['longest_streak']} days")
        col4.metric("Best Study Day", wrapped["best_day"] or "N/A")

        col5, col6, col7 = st.columns(3)
        col5.metric("Top Subject", wrapped["top_subject"] or "N/A")
        col6.metric("Top Language", wrapped["top_language"] or "N/A")
        col7.metric("Most Solved Topic", wrapped["top_topic"] or "N/A")

        summary_parts = [f"In {wrapped['period_label']}, you logged **{wrapped['study_hours']} hours** of study"]
        if wrapped["top_subject"]:
            summary_parts.append(f"mostly on **{wrapped['top_subject']}**")
        summary_parts.append(f"and solved **{wrapped['problems_solved']} problems**")
        if wrapped["top_language"]:
            summary_parts.append(f"mainly in **{wrapped['top_language']}**")
        summary = " ".join(summary_parts) + "."
        if wrapped["weakest_topic"] and wrapped["weakest_topic"] != wrapped["top_topic"]:
            summary += f" **{wrapped['weakest_topic']}** looks like an area to focus on next month."

        st.success(summary)

with yearly_tab:
    year_options = list(range(today.year, today.year - 5, -1))
    selected_year = st.selectbox("Select year", year_options, index=0)

    wrapped = yearly_wrapped(study_df, coding_df, selected_year)

    if not wrapped["has_data"]:
        st.info(f"No activity recorded for {wrapped['period_label']} yet.")
    else:
        st.header(f"YOUR {wrapped['period_label']} WRAPPED")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Study Hours", wrapped["study_hours"])
        col2.metric("Total Problems Solved", wrapped["problems_solved"])
        col3.metric("Longest Streak", f"{wrapped['longest_streak']} days")

        col4, col5, col6 = st.columns(3)
        col4.metric("Best Month", wrapped["best_month"] or "N/A")
        col5.metric("Most Productive Day", wrapped["best_day"] or "N/A")
        col6.metric("Most Used Language", wrapped["top_language"] or "N/A")

        st.metric("Most Practiced Topic", wrapped["top_topic"] or "N/A")

        st.success(
            f"You put in **{wrapped['study_hours']} hours** and solved "
            f"**{wrapped['problems_solved']} problems** in {wrapped['period_label']}. "
            f"Your best month was **{wrapped['best_month']}** -- keep that momentum going!"
        )
