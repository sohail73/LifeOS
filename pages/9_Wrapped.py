"""
pages/7_Wrapped.py

Monthly and Yearly Wrapped -- a Spotify-Wrapped-style summary of the
user's period, generated live from study_sessions/coding_logs (see
analytics/wrapped.py).
"""

from datetime import date

import streamlit as st

from analytics.wrapped import get_available_months, monthly_wrapped, yearly_wrapped
from auth.session import current_user_id, current_user_name, require_login
from database.queries import get_coding_logs_df, get_snapshots_df, get_study_sessions_df
from database.queries import get_avatar_base64
from utils.ui import kpi_card_row, render_sidebar_branding

st.set_page_config(page_title="Wrapped - LifeOS", page_icon="⚡", layout="wide")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
st.title("Wrapped")

study_df = get_study_sessions_df(user_id)
coding_df = get_coding_logs_df(user_id)

today = date.today()
monthly_tab, yearly_tab, journey_tab = st.tabs(["Monthly Wrapped", "Yearly Wrapped", "Your Journey"])

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
        st.header(f"{wrapped['period_label'].upper()} WRAPPED")

        kpi_card_row([
            {"icon": "", "label": "Study Hours", "value": wrapped["study_hours"]},
            {"icon": "", "label": "Problems Solved", "value": wrapped["problems_solved"]},
            {"icon": "", "label": "Longest Streak", "value": f"{wrapped['longest_streak']} days"},
            {"icon": "", "label": "Best Study Day", "value": wrapped["best_day"] or "N/A"},
        ])
        kpi_card_row([
            {"icon": "", "label": "Top Subject", "value": wrapped["top_subject"] or "N/A"},
            {"icon": "", "label": "Top Language", "value": wrapped["top_language"] or "N/A"},
            {"icon": "", "label": "Most Solved Topic", "value": wrapped["top_topic"] or "N/A"},
        ])

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

        kpi_card_row([
            {"icon": "", "label": "Total Study Hours", "value": wrapped["study_hours"]},
            {"icon": "", "label": "Total Problems Solved", "value": wrapped["problems_solved"]},
            {"icon": "", "label": "Longest Streak", "value": f"{wrapped['longest_streak']} days"},
        ])
        kpi_card_row([
            {"icon": "", "label": "Best Month", "value": wrapped["best_month"] or "N/A"},
            {"icon": "", "label": "Most Productive Day", "value": wrapped["best_day"] or "N/A"},
            {"icon": "", "label": "Most Used Language", "value": wrapped["top_language"] or "N/A"},
        ])
        kpi_card_row([
            {"icon": "", "label": "Most Practiced Topic", "value": wrapped["top_topic"] or "N/A"},
        ])

        st.success(
            f"You put in **{wrapped['study_hours']} hours** and solved "
            f"**{wrapped['problems_solved']} problems** in {wrapped['period_label']}. "
            f"Your best month was **{wrapped['best_month']}** -- keep that momentum going!"
        )

with journey_tab:
    st.subheader("Your Journey")
    st.caption("Every month you've been active, in one scrollable timeline. Click a month to open it.")

    available_months = get_available_months(study_df, coding_df)
    monthly_snapshots = get_snapshots_df(user_id, snapshot_type="monthly")

    if not available_months:
        st.info("No activity yet -- your journey will show up here once you start logging study or coding.")
    else:
        for year, month in available_months:
            wrapped = monthly_wrapped(study_df, coding_df, year, month)
            if not wrapped["has_data"]:
                continue

            with st.expander(f"{wrapped['period_label']}"):
                kpi_card_row([
                    {"icon": "", "label": "Studied", "value": f"{wrapped['study_hours']}h"},
                    {"icon": "", "label": "Problems Solved", "value": wrapped["problems_solved"]},
                    {"icon": "", "label": "Best Streak", "value": f"{wrapped['longest_streak']}d"},
                ])

                detail_lines = []
                if wrapped["top_subject"]:
                    detail_lines.append(f"**What you studied most:** {wrapped['top_subject']}")
                if wrapped["best_day"]:
                    detail_lines.append(f"**Most productive day:** {wrapped['best_day']}")
                if wrapped["top_topic"]:
                    detail_lines.append(f"**Strongest topic:** {wrapped['top_topic']}")
                if wrapped["weakest_topic"] and wrapped["weakest_topic"] != wrapped["top_topic"]:
                    detail_lines.append(f"**Weakest topic:** {wrapped['weakest_topic']}")
                if wrapped["top_language"]:
                    detail_lines.append(f"**Most used language:** {wrapped['top_language']}")

                period_label_key = date(year, month, 1).strftime("%Y-%m")
                matching_snapshot = monthly_snapshots[monthly_snapshots["period_label"] == period_label_key]
                if not matching_snapshot.empty:
                    goal_pct = matching_snapshot.iloc[0]["goal_completion"]
                    detail_lines.append(f"**Goal completion that month:** {goal_pct:.0f}%")

                for line in detail_lines:
                    st.write(line)

                if not detail_lines:
                    st.caption("Not enough detail recorded for this month.")
