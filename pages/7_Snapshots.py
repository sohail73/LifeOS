"""
pages/6_Snapshots.py

Historical snapshots (product spec sections 31-34). A snapshot
freezes a period's key numbers so they don't change when new data
comes in later, which is what makes comparison and "Time Machine"
style browsing meaningful.

v0.1 keeps this on-demand: the user creates a snapshot for the
current week/month with a button, rather than a background
scheduler (which would need a process outside Streamlit's normal
request/response cycle).
"""

import streamlit as st

from analytics.snapshot import build_and_save_monthly_snapshot, build_and_save_weekly_snapshot
from auth.session import current_user_id, require_login
from database.queries import get_snapshots_df

st.set_page_config(page_title="Snapshots - LifeOS", page_icon="🕰️", layout="wide")
require_login()

user_id = current_user_id()
st.title("Snapshots")
st.caption("Freeze your current progress so you can look back on it later.")

col1, col2 = st.columns(2)
with col1:
    if st.button("Save This Week's Snapshot", use_container_width=True):
        snap = build_and_save_weekly_snapshot(user_id)
        st.success(f"Saved snapshot for {snap['period_label']}.")
with col2:
    if st.button("Save This Month's Snapshot", use_container_width=True):
        snap = build_and_save_monthly_snapshot(user_id)
        st.success(f"Saved snapshot for {snap['period_label']}.")

st.divider()

weekly_tab, monthly_tab, compare_tab = st.tabs(["Weekly", "Monthly", "Compare"])


def _render_snapshot_table(snapshot_type: str) -> None:
    df = get_snapshots_df(user_id, snapshot_type=snapshot_type)
    if df.empty:
        st.info(f"No {snapshot_type} snapshots saved yet.")
        return

    display = df.sort_values("period_start", ascending=False).copy()
    display["study_hours"] = display["study_hours"].round(2)
    display = display[
        ["period_label", "study_hours", "problems_solved", "current_streak", "goal_completion"]
    ]
    display.columns = ["Period", "Study Hours", "Problems Solved", "Streak (days)", "Goal Completion (%)"]
    st.dataframe(display, use_container_width=True, hide_index=True)


with weekly_tab:
    _render_snapshot_table("weekly")

with monthly_tab:
    _render_snapshot_table("monthly")

with compare_tab:
    st.subheader("Compare Two Snapshots")
    all_snapshots = get_snapshots_df(user_id)

    if len(all_snapshots) < 2:
        st.info("Save at least two snapshots to compare them.")
    else:
        options = {
            f"{row['period_label']} ({row['snapshot_type']})": row
            for _, row in all_snapshots.sort_values("period_start").iterrows()
        }
        labels = list(options.keys())

        c1, c2 = st.columns(2)
        with c1:
            first_label = st.selectbox("From", labels, index=0)
        with c2:
            second_label = st.selectbox("To", labels, index=len(labels) - 1)

        first, second = options[first_label], options[second_label]

        def _pct_change(old: float, new: float) -> str:
            if old == 0:
                return "N/A" if new == 0 else "+∞%"
            change = (new - old) / old * 100
            sign = "+" if change >= 0 else ""
            return f"{sign}{change:.0f}%"

        metrics = [
            ("Study Hours", "study_hours"),
            ("Problems Solved", "problems_solved"),
            ("Streak (days)", "current_streak"),
            ("Goal Completion (%)", "goal_completion"),
        ]

        st.write(f"**{first_label} → {second_label}**")
        m_cols = st.columns(len(metrics))
        for col, (label, key) in zip(m_cols, metrics):
            old_val, new_val = first[key], second[key]
            col.metric(label, f"{new_val:g}", _pct_change(old_val, new_val))
