"""
pages/1_Dashboard.py

The single "how am I doing?" screen: an all-time overall-performance
overview, an automatic weekly recap, today's/week's/month's numbers,
recent activity, a LeetCode-style coding streak, upcoming goal
deadlines, and every active long-term goal as a manageable card
(check off topics, reschedule, extend deadlines -- shared with the
Goals & Tasks page via widgets/goal_widgets.py).
"""

from datetime import date, timedelta

import streamlit as st

from analytics import coding_analytics as ca
from analytics import study_analytics as sa
from analytics.insights import generate_weekly_summary
from analytics.tasks_analytics import goal_progress
from auth.session import current_user_name, require_login, current_user_id
from database.queries import (
    get_avatar_base64,
    get_coding_logs_df,
    get_custom_quote,
    get_goals,
    get_long_term_goals,
    get_projects,
    get_study_sessions_df,
    get_subjects,
    get_tasks_df,
    get_tasks_for_date,
)
from utils.helper import format_duration, get_daily_quote
from utils.ui import kpi_card_row, progress_bar_html, render_sidebar_branding
from widgets.charts import activity_heatmap
from widgets.goal_widgets import render_goal_card
from widgets.task_widgets import render_task_checklist

st.set_page_config(page_title="Dashboard - LifeOS", page_icon="⚡", layout="wide")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
st.title("Dashboard")
st.caption(f"Here's where things stand today, {current_user_name()}.")

today = date.today()

# ---------------------------------------------------------------------------
# Today's Tasks -- front and center, so it's the first thing you see
# ---------------------------------------------------------------------------
subjects = get_subjects(user_id)
subject_names = [s["name"] for s in subjects]
subject_lookup = {s["name"]: s["id"] for s in subjects}
today_tasks = get_tasks_for_date(user_id, today.isoformat())

tasks_col, quote_col = st.columns([3, 1])

with tasks_col:
    st.subheader("Today's Tasks")
    if today_tasks:
        render_task_checklist(
            user_id, today_tasks, subject_names, subject_lookup,
            key_prefix="dashtoday", task_date=today, compact=True,
        )
    else:
        st.caption("Nothing scheduled for today. Add tasks on the Goals & Tasks page.")

with quote_col:
    st.subheader("Today's Motivation")
    quote_text, quote_author = get_daily_quote(get_custom_quote(user_id))
    with st.container(border=True):
        st.markdown(f"*{quote_text}*")
        if quote_author:
            st.caption(f"— {quote_author}")

st.divider()

study_df = get_study_sessions_df(user_id)
coding_df = get_coding_logs_df(user_id)
goals = get_goals(user_id)
long_term_goals = get_long_term_goals(user_id)
projects = get_projects(user_id)

if study_df.empty and coding_df.empty:
    st.info(
        "**No activity yet.**\n\n"
        "Start your first study session or log a solved problem to unlock your dashboard."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Overall Performance -- the one-glance "how am I doing overall" summary
# ---------------------------------------------------------------------------
st.subheader("Overall Performance")

all_time_hours = round(sa.total_minutes(study_df) / 60, 1)
all_time_problems = ca.total_problems(coding_df)
active_goals_count = sum(1 for g in long_term_goals if g["end_date"] >= today.isoformat())
projects_in_progress = sum(1 for p in projects if p["status"] == "In Progress")
study_current_streak, study_longest_streak = sa.get_streaks(study_df)
coding_current_streak, coding_longest_streak = ca.get_streaks(coding_df)

kpi_card_row([
    {"icon": " ", "label": "All-Time Study", "value": f"{all_time_hours}h"},
    {"icon": " ", "label": "All-Time Problems", "value": all_time_problems},
    {"icon": " ", "label": "Study Streak", "value": f"{study_current_streak}d", "sub": f"best {study_longest_streak}d"},
    {"icon": " ", "label": "Coding Streak", "value": f"{coding_current_streak}d", "sub": f"best {coding_longest_streak}d"},
    {"icon": " ", "label": "Active Goals", "value": active_goals_count},
    {"icon": " ", "label": "Projects In Progress", "value": projects_in_progress},
])

# ---------------------------------------------------------------------------
# Weekly summary -- auto-generated from this week's snapshot vs last week's
# ---------------------------------------------------------------------------
weekly_summary = generate_weekly_summary(user_id)
if weekly_summary:
    st.markdown("##### Your Week So Far")
    with st.container(border=True):
        st.write(weekly_summary["summary_text"])

st.divider()

# --- Today's snapshot ---
today_minutes = sa.minutes_on_date(study_df, today)
today_problems = ca.problems_on_date(coding_df, today)

study_goal = goals["daily_study_minutes_goal"]
problems_goal = goals["daily_problems_goal"]
study_goal_pct = min(today_minutes / study_goal, 1.0) if study_goal else 0.0
problems_goal_pct = min(today_problems / problems_goal, 1.0) if problems_goal else 0.0
overall_goal_pct = round((study_goal_pct + problems_goal_pct) / 2 * 100, 1)

kpi_card_row([
    {"icon": " ", "label": "Today's Study Time", "value": format_duration(today_minutes)},
    {"icon": " ", "label": "Problems Solved Today", "value": today_problems},
    {"icon": " ", "label": "Current Streak", "value": f"{study_current_streak} days"},
    {"icon": " ", "label": "Longest Streak", "value": f"{study_longest_streak} days"},
])

progress_bar_html(overall_goal_pct, label="Today's goal completion")

st.divider()

# --- Weekly / monthly totals ---
week_start = today - timedelta(days=6)
month_start = today.replace(day=1)

week_minutes = sa.minutes_since(study_df, week_start)
month_minutes = sa.minutes_since(study_df, month_start)
week_problems = ca.problems_since(coding_df, week_start)
month_problems = ca.problems_since(coding_df, month_start)

kpi_card_row([
    {"icon": " ", "label": "This Week's Study Time", "value": format_duration(week_minutes)},
    {"icon": " ", "label": "This Month's Study Time", "value": format_duration(month_minutes)},
    {"icon": " ", "label": "Problems This Week", "value": week_problems},
    {"icon": " ", "label": "Problems This Month", "value": month_problems},
])

st.divider()

# --- Recent activity ---
st.subheader("Recent Activity")
recent_col1, recent_col2 = st.columns(2)

with recent_col1:
    with st.container(border=True):
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
    with st.container(border=True):
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

# --- Overall app activity streak, LeetCode-profile style but for the whole app ---
if not study_df.empty or not coding_df.empty:
    st.divider()
    st.subheader("App Streak")

    app_current_streak, app_longest_streak = sa.combined_streak(study_df, coding_df)

    kpi_card_row([
        {"icon": " ", "label": "Total Studied", "value": f"{all_time_hours}h"},
        {"icon": " ", "label": "Total Solved", "value": all_time_problems},
        {"icon": " ", "label": "Current Streak", "value": f"{app_current_streak} days"},
        {"icon": " ", "label": "Max Streak", "value": f"{app_longest_streak} days"},
    ])

    activity_df = sa.combined_daily_activity(study_df, coding_df, days=182)
    st.plotly_chart(
        activity_heatmap(activity_df, title="Activity -- Last 6 Months"),
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Upcoming deadlines -- goals ending within 3 days and not yet complete
# ---------------------------------------------------------------------------
upcoming = []
for goal in long_term_goals:
    end = date.fromisoformat(goal["end_date"])
    days_left = (end - today).days
    if 0 <= days_left <= 3:
        goal_tasks = get_tasks_df(user_id, goal_id=goal["id"])
        progress = goal_progress(goal, goal_tasks)
        if progress["completion_pct"] < 100:
            upcoming.append((goal, days_left, progress["completion_pct"]))

if upcoming:
    st.divider()
    st.subheader("⏳ Upcoming Deadlines")
    for goal, days_left, pct in upcoming:
        due_text = "today" if days_left == 0 else f"in {days_left} day(s)"
        st.warning(f"**{goal['title']}** is due {due_text} and is {pct:.0f}% complete.")

# ---------------------------------------------------------------------------
# Active long-term goals -- full manage-in-place cards
# ---------------------------------------------------------------------------
if long_term_goals:
    st.divider()
    st.subheader("Active Goals")

    sorted_goals = sorted(long_term_goals, key=lambda g: g["end_date"])
    for goal in sorted_goals:
        render_goal_card(
            user_id, goal, subject_names, subject_lookup,
            context_key="dash", show_delete=False, editable=False,
        )

# ---------------------------------------------------------------------------
# Calendar -- pick any date (Streamlit's own calendar picker) and see
# what happened/what's due that day
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Calendar")
picked_date = st.date_input("Pick a date", value=today, key="dashboard_calendar_pick")

all_tasks_df = get_tasks_df(user_id)
day_study_minutes = sa.minutes_on_date(study_df, picked_date)
day_problems = ca.problems_on_date(coding_df, picked_date)
day_tasks_total, day_tasks_done = 0, 0
if not all_tasks_df.empty:
    day_tasks = all_tasks_df[all_tasks_df["task_date"].dt.date == picked_date]
    day_tasks_total = len(day_tasks)
    day_tasks_done = int(day_tasks["is_done"].sum()) if day_tasks_total else 0

goal_events = []
for g in long_term_goals:
    if g["start_date"] == picked_date.isoformat():
        goal_events.append(f" {g['title']} starts")
    if g["end_date"] == picked_date.isoformat():
        goal_events.append(f"🏁 {g['title']} due")

with st.container(border=True):
    st.markdown(f"**{picked_date.strftime('%A, %d %B %Y')}**")
    nothing_recorded = day_study_minutes == 0 and day_problems == 0 and day_tasks_total == 0 and not goal_events
    if nothing_recorded:
        st.caption("Nothing recorded for this date.")
    else:
        if day_study_minutes > 0:
            st.write(f"Studied {format_duration(day_study_minutes)}")
        if day_problems > 0:
            st.write(f"Solved {day_problems} problem(s)")
        if day_tasks_total > 0:
            st.write(f"{day_tasks_done}/{day_tasks_total} task(s) done")
        for event in goal_events:
            st.write(event)
