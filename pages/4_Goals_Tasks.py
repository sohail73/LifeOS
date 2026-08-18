"""
pages/4_Goals_Tasks.py

Two connected ideas:

1. Daily Tasks -- a simple to-do list for any date ("today I need to
   study DBMS"), optionally linked to a long-term goal. Marking one
   complete asks how long you actually studied and which subject, and
   logs that as a real study session (so Analytics/Dashboard reflect
   it, not just a checkbox) -- see complete_task_with_session. A task
   can also be rescheduled to a different date if it slipped.
2. Long-Term Goals -- a milestone with a start/end date ("crack the
   job in 60 days", "finish DSA in 3 months"). You can list the
   subjects/topics it should cover, and creating it auto-generates one
   task per day cycling through them. Each goal's card (also shown on
   the Dashboard) expands into a full manager: check off topics,
   reschedule any of them, add more, and extend the deadline -- see
   widgets/goal_widgets.py, shared with the Dashboard.
"""

from datetime import date, timedelta

import streamlit as st

from analytics.goal_maintenance import generate_topic_tasks, parse_topic_line
from analytics.tasks_analytics import daily_completion_counts, task_streak
from auth.session import current_user_id, current_user_name, require_login
from database.queries import (
    add_long_term_goal,
    add_task,
    get_avatar_base64,
    get_long_term_goals,
    get_subjects,
    get_tasks_df,
    get_tasks_for_date,
)
from utils.ui import render_sidebar_branding
from widgets.charts import calendar_heatmap
from widgets.goal_widgets import render_goal_card
from widgets.task_widgets import render_task_checklist

st.set_page_config(page_title="Goals & Tasks - LifeOS", page_icon="⚡", layout="wide")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
st.title("Goals & Tasks")

tasks_tab, goals_tab, streak_tab = st.tabs(["Today's Tasks", "Long-Term Goals", "Streak"])

# ---------------------------------------------------------------------------
# Daily Tasks
# ---------------------------------------------------------------------------
with tasks_tab:
    all_goals = get_long_term_goals(user_id)
    goal_options = {"No goal": None}
    goal_options.update({g["title"]: g["id"] for g in all_goals})

    subjects = get_subjects(user_id)
    subject_names = [s["name"] for s in subjects]
    subject_lookup = {s["name"]: s["id"] for s in subjects}

    selected_date = st.date_input("Date", value=date.today())
    day_tasks = get_tasks_for_date(user_id, selected_date.isoformat())

    st.subheader(f"Tasks for {selected_date.strftime('%d %b %Y')}")

    render_task_checklist(
        user_id, day_tasks, subject_names, subject_lookup,
        key_prefix="goalspage", task_date=selected_date, compact=False,
    )

    st.divider()
    with st.form("add_task_form"):
        new_task_title = st.text_input("New task", placeholder="e.g. Study DBMS chapter 3")
        linked_goal_label = st.selectbox("Link to a goal (optional)", list(goal_options.keys()))
        set_time = st.checkbox("Set a planned time (optional)")
        time_col1, time_col2 = st.columns(2)
        with time_col1:
            planned_start = st.time_input("Start time", disabled=not set_time, key="planned_start_input")
        with time_col2:
            planned_end = st.time_input("End time", disabled=not set_time, key="planned_end_input")
        add_task_submitted = st.form_submit_button("Add Task", use_container_width=True)

    if add_task_submitted:
        if not new_task_title.strip():
            st.error("Task can't be empty.")
        else:
            add_task(
                user_id,
                new_task_title,
                selected_date.isoformat(),
                goal_options[linked_goal_label],
                planned_start_time=planned_start.strftime("%H:%M") if set_time else None,
                planned_end_time=planned_end.strftime("%H:%M") if set_time else None,
            )
            st.success("Task added.")
            st.rerun()

# ---------------------------------------------------------------------------
# Long-Term Goals
# ---------------------------------------------------------------------------
with goals_tab:
    st.subheader("Your Goals")
    goals_list = get_long_term_goals(user_id)

    if not goals_list:
        st.caption("No long-term goals yet -- create one below.")
    else:
        for goal in goals_list:
            render_goal_card(user_id, goal, subject_names, subject_lookup, context_key="goals", show_delete=True)

    st.divider()
    st.subheader("Create a New Goal")

    with st.form("add_goal_form"):
        goal_title = st.text_input("Goal title", placeholder="e.g. Crack the job / Finish DSA")
        col1, col2 = st.columns(2)
        with col1:
            goal_start = st.date_input("Start date", value=date.today(), key="goal_start")
        with col2:
            duration_days = st.number_input(
                "Duration (days)", min_value=1, max_value=730, value=30,
                help="e.g. 30 for a month, 90 for 3 months, 180 for 6 months",
            )
        goal_notes = st.text_area("Notes (optional)")
        auto_generate = st.checkbox(
            "Auto-create tasks for this goal",
            value=True,
            help="Adds one task per day so you can track it on the Streak tab from day one.",
        )
        topics_text = st.text_area(
            "Subjects/topics to cover (one per line, optional)",
            placeholder="Arrays: 5\nTrees\nGraphs",
            help=(
                "Plain line = cycles daily across the Duration above. Add ': <n>' for a fixed "
                "block of n consecutive days (e.g. 'Arrays: 5'). Optional patterns if you need "
                "them: ': alternate' (every other day), ': every 3' (every 3rd day), "
                "': Sunday' (that weekday only), or ': dates 2026-08-20, 2026-08-27' (exact dates). "
                "Everything here is optional -- leave it blank for a plain goal."
            ),
        )
        daily_task_title = st.text_input(
            "Daily task title (used only if no topics are listed above)",
            placeholder="Defaults to the goal title",
        )
        goal_submitted = st.form_submit_button("Create Goal", use_container_width=True)

    if goal_submitted:
        if not goal_title.strip():
            st.error("Goal title can't be empty.")
        else:
            parsed_topics = [
                parse_topic_line(line) for line in topics_text.splitlines() if line.strip()
            ]
            parsed_topics = [t for t in parsed_topics if t]

            if auto_generate and parsed_topics and all(t["schedule"] == "block" for t in parsed_topics):
                # Every topic is a fixed block -- auto-compute the goal's
                # total length from the day counts (no Duration needed).
                total_days = sum(t["block_days"] for t in parsed_topics)
                goal_end = goal_start + timedelta(days=total_days - 1)
                new_goal_id = add_long_term_goal(
                    user_id, goal_title, goal_start.isoformat(), goal_end.isoformat(), goal_notes
                )
                cursor_date = goal_start
                for t in parsed_topics:
                    for _ in range(t["block_days"]):
                        add_task(user_id, t["name"], cursor_date.isoformat(), new_goal_id)
                        cursor_date += timedelta(days=1)
                st.success(
                    f"Created '{goal_title}' ({goal_start} to {goal_end}) -- {total_days} days "
                    f"across {len(parsed_topics)} topic(s)."
                )
                st.rerun()
            elif auto_generate and parsed_topics:
                goal_end = goal_start + timedelta(days=int(duration_days) - 1)
                new_goal_id = add_long_term_goal(
                    user_id, goal_title, goal_start.isoformat(), goal_end.isoformat(), goal_notes
                )
                generated = generate_topic_tasks(goal_start, int(duration_days), parsed_topics)
                for day_iso, topic_name in generated:
                    add_task(user_id, topic_name, day_iso, new_goal_id)
                st.success(
                    f"Created '{goal_title}' ({goal_start} to {goal_end}) -- {len(generated)} tasks "
                    f"across {len(parsed_topics)} topic(s)."
                )
                st.rerun()
            else:
                goal_end = goal_start + timedelta(days=int(duration_days) - 1)
                new_goal_id = add_long_term_goal(
                    user_id, goal_title, goal_start.isoformat(), goal_end.isoformat(), goal_notes
                )
                if auto_generate and daily_task_title.strip():
                    for offset in range(int(duration_days)):
                        day = goal_start + timedelta(days=offset)
                        add_task(user_id, daily_task_title.strip(), day.isoformat(), new_goal_id)
                    st.success(
                        f"Created '{goal_title}' ({goal_start} to {goal_end}) with "
                        f"{int(duration_days)} daily tasks."
                    )
                else:
                    st.success(f"Created '{goal_title}' ({goal_start} to {goal_end}).")
                st.rerun()

# ---------------------------------------------------------------------------
# Streak
# ---------------------------------------------------------------------------
with streak_tab:
    st.subheader("Task Completion Streak")

    goals_list = get_long_term_goals(user_id)
    scope_options = {"All tasks": None}
    scope_options.update({g["title"]: g["id"] for g in goals_list})
    scope_label = st.selectbox("Scope", list(scope_options.keys()))

    tasks_df = get_tasks_df(user_id, goal_id=scope_options[scope_label])

    if tasks_df.empty:
        st.info(
            "**No tasks yet.**\n\n"
            "Add a task in the **Today's Tasks** tab, or create a goal with "
            "auto-generated daily tasks in **Long-Term Goals**."
        )
    else:
        current_streak, longest_streak = task_streak(tasks_df)
        total = len(tasks_df)
        done = int(tasks_df["is_done"].sum())

        col1, col2, col3 = st.columns(3)
        col1.metric("Current Streak", f"{current_streak} days")
        col2.metric("Longest Streak", f"{longest_streak} days")
        col3.metric("Tasks Completed", f"{done}/{total}")

        heatmap_df = daily_completion_counts(tasks_df)
        if not heatmap_df.empty:
            st.plotly_chart(
                calendar_heatmap(
                    heatmap_df,
                    date_col="task_date",
                    value_col="completed_count",
                    title="Completed Tasks by Day",
                    colorscale="Greens",
                    hover_suffix=" done",
                ),
                use_container_width=True,
            )
        else:
            st.caption("Complete a few tasks to see your streak heatmap here.")
