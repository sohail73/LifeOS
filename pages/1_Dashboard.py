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

import time

import streamlit as st

from analytics import coding_analytics as ca
from analytics import study_analytics as sa
from analytics.insights import generate_weekly_summary
from analytics.tasks_analytics import goal_progress
from auth.session import current_user_name, require_login, current_user_id
from database.queries import (
    add_leave_days,
    delete_leave_day,
    get_avatar_base64,
    get_coding_logs_df,
    get_custom_quote,
    get_goals,
    get_leave_dates,
    get_leave_days,
    get_long_term_goals,
    get_pinned_job_target,
    get_projects,
    get_study_sessions_df,
    get_subjects,
    get_tasks_df,
    get_tasks_for_date,
)
from utils.helper import format_duration, get_daily_quote
from utils.streak_badge import badge_html as streak_badge_html
from utils.ui import page_header, countdown_banner_html, kpi_card_row, progress_bar_html, render_sidebar_branding
from widgets.charts import activity_heatmap
from widgets.goal_widgets import render_goal_card
from widgets.task_widgets import render_task_checklist

_page_started = time.perf_counter()  # for the small "built in X s" note at the very bottom
st.set_page_config(page_title="Dashboard - LifeOS", page_icon="⚡", layout="wide")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
header_left, header_right = st.columns([3, 2])
with header_left:
    page_header("Dashboard", eyebrow="Overview")
    st.caption(f"Here's where things stand today, {current_user_name()}.")
streak_badge_slot = header_right.empty()  # filled below, once study data and the daily goal are loaded

today = date.today()

# ---------------------------------------------------------------------------
# Pinned job-target countdown -- front and center, so the "why am I
# doing all this" target is the very first thing you see
# ---------------------------------------------------------------------------
pinned_job = get_pinned_job_target(user_id)
if pinned_job:
    job_title = pinned_job["title"]
    if pinned_job["company"]:
        job_title += f" -- {pinned_job['company']}"
    package_sub = f"Target package: {pinned_job['target_package']}" if pinned_job["target_package"] else ""

    if pinned_job["status"] == "Achieved":
        countdown_banner_html(
            title=job_title,
            sub=(package_sub + " -- " if package_sub else "") + "You got it!",
            number="Done",
            number_label="achieved",
            variant="achieved",
        )
    elif pinned_job["deadline"]:
        deadline_date = date.fromisoformat(pinned_job["deadline"])
        days_left = (deadline_date - today).days
        if days_left > 0:
            countdown_banner_html(
                title=job_title,
                sub=(package_sub + " -- " if package_sub else "") + f"Deadline: {pinned_job['deadline']}",
                number=str(days_left),
                number_label=f"day{'s' if days_left != 1 else ''} left",
            )
        elif days_left == 0:
            countdown_banner_html(
                title=job_title,
                sub=(package_sub + " -- " if package_sub else "") + "The deadline is today",
                number="0",
                number_label="days left",
                variant="overdue",
            )
        else:
            countdown_banner_html(
                title=job_title,
                sub=(package_sub + " -- " if package_sub else "") + f"Deadline was {pinned_job['deadline']}",
                number=str(abs(days_left)),
                number_label="days overdue",
                variant="overdue",
            )
    elif package_sub:
        countdown_banner_html(title=job_title, sub=package_sub, number="--", number_label="no deadline set")


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

# Top-right badge: daily study-goal streak (faded until today's goal is reached)
goal_streak_info = sa.goal_streak(
    study_df, goals["daily_study_minutes_goal"], excused_dates=get_leave_dates(user_id), today=today
)
streak_badge_slot.markdown(streak_badge_html(goal_streak_info), unsafe_allow_html=True)

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
    {"icon": " ", "label": "Study Streak", "value": f"{study_current_streak}d", "sub": f"best {study_longest_streak}d", "color": "green"},
    {"icon": " ", "label": "Coding Streak", "value": f"{coding_current_streak}d", "sub": f"best {coding_longest_streak}d", "color": "green"},
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
    {"icon": " ", "label": "Current Streak", "value": f"{study_current_streak} days", "color": "green"},
    {"icon": " ", "label": "Longest Streak", "value": f"{study_longest_streak} days", "color": "green"},
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
        {"icon": " ", "label": "Current Streak", "value": f"{app_current_streak} days", "color": "green"},
        {"icon": " ", "label": "Max Streak", "value": f"{app_longest_streak} days", "color": "green"},
    ])

    activity_df = sa.combined_daily_activity(study_df, coding_df, days=182)
    st.plotly_chart(
        activity_heatmap(activity_df, title="Activity -- Last 6 Months"),
        use_container_width=True,
    )

    # --- Leave days: away / couldn't log -> streak stays safe, cell turns blue ---
    with st.expander("🔵 Mark leave / away days (keeps your streak safe)"):
        st.caption(
            "Travelling, unwell, or just couldn't log? Mark those days here -- they show up "
            "in blue on the streak charts and never break your streak. You can mark past days "
            "(to fix a streak that broke by mistake) or upcoming ones."
        )
        with st.form("leave_form", clear_on_submit=True):
            leave_range = st.date_input(
                "Day or date range",
                value=(today, today),
                help="Pick one day, or click a start and an end date for several days.",
            )
            leave_reason = st.text_input("Reason (optional)", placeholder="e.g. Out of station")
            leave_submitted = st.form_submit_button("Save leave", use_container_width=True)

        if leave_submitted:
            if isinstance(leave_range, (tuple, list)):
                picked = list(leave_range)
            else:
                picked = [leave_range]
            if not picked:
                st.warning("Pick a date first.")
            else:
                leave_start, leave_end = picked[0], picked[-1]
                added = add_leave_days(user_id, leave_start.isoformat(), leave_end.isoformat(), leave_reason)
                st.success(f"Marked {added} day(s) as leave." if added else "Those days were already marked as leave.")
                st.rerun()

        leave_rows = get_leave_days(user_id)
        if leave_rows:
            st.markdown("**Your leave days**")
            for row in leave_rows[:15]:
                lcol1, lcol2 = st.columns([5, 1])
                label = date.fromisoformat(row["leave_date"]).strftime("%d %b %Y")
                lcol1.write(f"{label}" + (f" · {row['reason']}" if row["reason"] else ""))
                if lcol2.button("Remove", key=f"leave_del_{row['id']}"):
                    delete_leave_day(user_id, row["id"])
                    st.rerun()
            if len(leave_rows) > 15:
                st.caption(f"Showing the latest 15 of {len(leave_rows)} leave days.")

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

st.caption(f"Page built on the server in {time.perf_counter() - _page_started:.2f}s")
