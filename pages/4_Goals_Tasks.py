"""
pages/4_Goals_Tasks.py

Two connected ideas:

1. Daily Tasks -- a simple to-do list for any date ("today I need to
   study DBMS"), optionally linked to a long-term goal.
2. Long-Term Goals -- a milestone with a start/end date ("crack the
   job in 60 days", "finish DSA in 3 months"). Creating one can
   auto-generate a daily task for every day in its range, which is
   then tracked with a streak + calendar heatmap on the Streak tab.
"""

from datetime import date, timedelta

import streamlit as st

from analytics.tasks_analytics import daily_completion_counts, goal_progress, task_streak
from auth.session import current_user_id, require_login
from database.queries import (
    add_long_term_goal,
    add_task,
    delete_long_term_goal,
    delete_task,
    get_long_term_goals,
    get_tasks_df,
    get_tasks_for_date,
    toggle_task,
)
from widgets.charts import calendar_heatmap

st.set_page_config(page_title="Goals & Tasks - LifeOS", page_icon="🎯", layout="wide")
require_login()

user_id = current_user_id()
st.title("Goals & Tasks")

tasks_tab, goals_tab, streak_tab = st.tabs(["Today's Tasks", "Long-Term Goals", "Streak"])

# ---------------------------------------------------------------------------
# Daily Tasks
# ---------------------------------------------------------------------------
with tasks_tab:
    all_goals = get_long_term_goals(user_id)
    goal_options = {"No goal": None}
    goal_options.update({g["title"]: g["id"] for g in all_goals})

    selected_date = st.date_input("Date", value=date.today())
    day_tasks = get_tasks_for_date(user_id, selected_date.isoformat())

    st.subheader(f"Tasks for {selected_date.strftime('%d %b %Y')}")

    if not day_tasks:
        st.caption("No tasks for this date yet -- add one below.")
    else:
        for task in day_tasks:
            col_check, col_title, col_delete = st.columns([1, 5, 1])
            new_done = col_check.checkbox("", value=bool(task["is_done"]), key=f"task_check_{task['id']}")
            if new_done != bool(task["is_done"]):
                toggle_task(user_id, task["id"], new_done)
                st.rerun()

            label = task["title"]
            if task["goal_title"]:
                label += f"  ·  🏁 {task['goal_title']}"
            if new_done:
                col_title.markdown(f"~~{label}~~")
            else:
                col_title.write(label)

            if col_delete.button("🗑️", key=f"del_task_{task['id']}"):
                delete_task(user_id, task["id"])
                st.rerun()

    st.divider()
    with st.form("add_task_form"):
        new_task_title = st.text_input("New task", placeholder="e.g. Study DBMS chapter 3")
        linked_goal_label = st.selectbox("Link to a goal (optional)", list(goal_options.keys()))
        add_task_submitted = st.form_submit_button("Add Task", use_container_width=True)

    if add_task_submitted:
        if not new_task_title.strip():
            st.error("Task can't be empty.")
        else:
            add_task(user_id, new_task_title, selected_date.isoformat(), goal_options[linked_goal_label])
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
            goal_tasks_df = get_tasks_df(user_id, goal_id=goal["id"])
            progress = goal_progress(goal, goal_tasks_df)

            with st.container(border=True):
                title_col, delete_col = st.columns([5, 1])
                title_col.markdown(f"**🏁 {goal['title']}**")
                if delete_col.button("🗑️ Delete", key=f"del_goal_{goal['id']}"):
                    delete_long_term_goal(user_id, goal["id"])
                    st.rerun()

                st.caption(f"{goal['start_date']} → {goal['end_date']} ({progress['total_days']} days)")
                if goal["notes"]:
                    st.caption(goal["notes"])

                st.progress(
                    progress["completion_pct"] / 100,
                    text=f"{progress['completed_tasks']}/{progress['total_tasks']} tasks done "
                    f"({progress['completion_pct']}%)",
                )

                info_cols = st.columns(2)
                info_cols[0].caption(f"Day {progress['days_elapsed']} of {progress['total_days']}")
                if progress["is_overdue"]:
                    info_cols[1].caption("⚠️ Past end date, not fully complete")
                else:
                    info_cols[1].caption(f"{progress['days_remaining']} days remaining")

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
            "Auto-create a daily task for every day in this range",
            help="Adds one task per day (using the title below, or the goal title) so you "
                 "can track it on the Streak tab from day one.",
        )
        daily_task_title = st.text_input(
            "Daily task title (used if auto-creating tasks)", placeholder="Defaults to the goal title"
        )
        goal_submitted = st.form_submit_button("Create Goal", use_container_width=True)

    if goal_submitted:
        if not goal_title.strip():
            st.error("Goal title can't be empty.")
        else:
            goal_end = goal_start + timedelta(days=int(duration_days) - 1)
            new_goal_id = add_long_term_goal(
                user_id, goal_title, goal_start.isoformat(), goal_end.isoformat(), goal_notes
            )

            if auto_generate:
                task_title = daily_task_title.strip() or goal_title.strip()
                for offset in range(int(duration_days)):
                    day = goal_start + timedelta(days=offset)
                    add_task(user_id, task_title, day.isoformat(), new_goal_id)
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
