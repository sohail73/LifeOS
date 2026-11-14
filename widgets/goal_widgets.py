"""
widgets/goal_widgets.py

Shared goal-detail widget: a progress card for one long-term goal
that expands into a full task manager -- check off topics (with the
same duration+subject popup as Today's Tasks), reschedule any task,
add new topics, delete tasks, and extend the goal's deadline. Used on
both the Goals & Tasks page and the Dashboard so goal management
works identically everywhere it appears.
"""

from datetime import date, timedelta

import streamlit as st

from analytics.tasks_analytics import goal_progress
from database.queries import (
    add_task,
    complete_task_with_session,
    delete_long_term_goal,
    delete_task,
    extend_goal_end_date,
    goal_has_completed_tasks,
    get_tasks_df,
    get_tasks_for_goal,
    goal_move_availability,
    move_goal_order,
    reschedule_task,
    set_goal_priority,
    shift_goal_start_date,
    toggle_task,
    uncomplete_task,
    update_goal_notes,
)
from analytics.goal_maintenance import pull_task_forward
from utils.ui import duration_input, priority_badge, progress_bar_html


def render_goal_card(
    user_id: int,
    goal: dict,
    subject_names: list[str],
    subject_lookup: dict,
    context_key: str,
    show_delete: bool = False,
    editable: bool = True,
) -> None:
    """
    context_key must be unique per place this is rendered (e.g. "dash"
    vs "goals") so widget keys don't collide when the same goal is
    shown on two different pages in the same session. show_delete
    controls whether a "Delete goal" button appears. editable=False
    (used on the Dashboard) hides every edit control -- extend, add
    description, check off/reschedule/delete tasks, add topics -- and
    shows the task list as plain read-only status text instead, with
    a link over to Goals & Tasks for actually managing it.
    """
    goal_tasks_df = get_tasks_df(user_id, goal_id=goal["id"])
    progress = goal_progress(goal, goal_tasks_df)
    extend_key = f"extend_{context_key}_{goal['id']}"
    start_key = f"start_{context_key}_{goal['id']}"
    edit_notes_key = f"edit_notes_{context_key}_{goal['id']}"

    with st.container(border=True):
        if editable and show_delete:
            title_col, up_col, down_col, start_col, extend_col, delete_col = st.columns([3, 1, 1, 2, 2, 2])
        elif editable:
            title_col, up_col, down_col, start_col, extend_col = st.columns([4, 1, 1, 2, 2])
            delete_col = None
        else:
            title_col = st.container()
            up_col = down_col = start_col = extend_col = delete_col = None

        title_col.markdown(f"**🏁 {goal['title']}** &nbsp; {priority_badge(goal.get('priority', 2))}", unsafe_allow_html=True)
        if editable:
            can_up, can_down = goal_move_availability(user_id, goal["id"])
            if up_col.button(
                "Up", key=f"goal_up_{context_key}_{goal['id']}", disabled=not can_up,
                help="Move up among goals of the same priority -- applies to every day's tasks, permanently.",
            ):
                move_goal_order(user_id, goal["id"], "up")
                st.rerun()
            if down_col.button(
                "Down", key=f"goal_down_{context_key}_{goal['id']}", disabled=not can_down,
                help="Move down among goals of the same priority -- applies to every day's tasks, permanently.",
            ):
                move_goal_order(user_id, goal["id"], "down")
                st.rerun()
        if editable and start_col.button(
            "Change start", key=f"start_btn_{context_key}_{goal['id']}",
            help="Move the whole goal (and all its tasks) to start on a different date.",
        ):
            st.session_state[start_key] = not st.session_state.get(start_key, False)
        if editable and extend_col.button("⏳ Extend", key=f"extend_btn_{context_key}_{goal['id']}"):
            st.session_state[extend_key] = not st.session_state.get(extend_key, False)
        if delete_col is not None and delete_col.button("🗑️ Delete", key=f"del_goal_{context_key}_{goal['id']}"):
            delete_long_term_goal(user_id, goal["id"])
            st.rerun()

        st.caption(
            f"{goal['start_date']} → {goal['end_date']} · "
            f"Day {progress['days_elapsed']} of {progress['total_days']}"
        )

        if goal.get("notes"):
            st.caption(goal["notes"])

        if editable:
            if st.button(
                "✏️ Edit description & priority" if goal.get("notes") else "✏️ Add description & priority",
                key=f"edit_notes_btn_{context_key}_{goal['id']}",
            ):
                st.session_state[edit_notes_key] = not st.session_state.get(edit_notes_key, False)

            if st.session_state.get(edit_notes_key):
                priority_labels = ["High", "Medium", "Low"]
                priority_values = {"High": 1, "Medium": 2, "Low": 3}
                current_priority = {1: "High", 2: "Medium", 3: "Low"}.get(goal.get("priority", 2), "Medium")
                with st.form(f"notes_form_{context_key}_{goal['id']}"):
                    new_notes = st.text_area(
                        "Description", value=goal.get("notes") or "", key=f"notes_input_{context_key}_{goal['id']}"
                    )
                    new_priority_label = st.selectbox(
                        "Priority", priority_labels, index=priority_labels.index(current_priority),
                        help="Every task under this goal inherits this priority automatically.",
                        key=f"priority_input_{context_key}_{goal['id']}",
                    )
                    save_notes = st.form_submit_button("Save")
                if save_notes:
                    update_goal_notes(user_id, goal["id"], new_notes)
                    set_goal_priority(user_id, goal["id"], priority_values[new_priority_label])
                    del st.session_state[edit_notes_key]
                    st.success("Updated.")
                    st.rerun()

        progress_bar_html(
            progress["completion_pct"],
            label=f"{progress['completed_tasks']}/{progress['total_tasks']} tasks done",
        )

        if progress["is_overdue"]:
            st.caption("⚠️ Past end date, not fully complete")
        else:
            st.caption(f"{progress['days_remaining']} days remaining")

        if editable and st.session_state.get(start_key):
            if goal_has_completed_tasks(user_id, goal["id"]):
                st.info(
                    "This goal already has completed tasks, so its start date can't be moved. "
                    "Use Extend for the deadline, or reschedule individual tasks."
                )
            else:
                old_start = date.fromisoformat(goal["start_date"])
                old_end = date.fromisoformat(goal["end_date"])
                new_start = st.date_input(
                    "New start date", value=date.today(),
                    min_value=date.today(), key=f"new_start_{context_key}_{goal['id']}",
                )
                shift = (new_start - old_start).days
                preview_end = old_end + timedelta(days=shift)
                st.caption(
                    f"The whole schedule moves {abs(shift)} day(s) {'earlier' if shift < 0 else 'later'}: "
                    f"{new_start.isoformat()} → {preview_end.isoformat()}"
                    if shift else "That's already the start date."
                )
                if st.button(
                    "Confirm New Start Date", key=f"confirm_start_{context_key}_{goal['id']}", disabled=shift == 0
                ):
                    try:
                        shift_goal_start_date(user_id, goal["id"], new_start.isoformat())
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        del st.session_state[start_key]
                        st.success(f"Goal now starts on {new_start.strftime('%d %b %Y')}.")
                        st.rerun()

        if editable and st.session_state.get(extend_key):
            current_end = date.fromisoformat(goal["end_date"])
            new_end = st.date_input(
                "New end date", value=current_end + timedelta(days=14),
                min_value=current_end, key=f"new_end_{context_key}_{goal['id']}",
            )
            if st.button("Confirm New Deadline", key=f"confirm_extend_{context_key}_{goal['id']}"):
                extend_goal_end_date(user_id, goal["id"], new_end.isoformat())
                del st.session_state[extend_key]
                st.success(f"Deadline moved to {new_end.strftime('%d %b %Y')}.")
                st.rerun()

        if not editable:
            _render_readonly_task_summary(user_id, goal["id"])
            return

        with st.expander(f"📋 View & manage all {progress['total_tasks']} topics/tasks"):
            all_tasks = get_tasks_for_goal(user_id, goal["id"])

            if not all_tasks:
                st.caption("No topics yet -- add one below.")
            else:
                for task in all_tasks:
                    _render_manageable_task_row(user_id, task, subject_names, subject_lookup, context_key, goal["id"])

            st.divider()
            with st.form(f"add_topic_form_{context_key}_{goal['id']}"):
                new_topic_title = st.text_input("New topic/task", key=f"new_topic_{context_key}_{goal['id']}")
                new_topic_date = st.date_input(
                    "Date", value=date.today(), key=f"new_topic_date_{context_key}_{goal['id']}"
                )
                add_topic_submitted = st.form_submit_button("Add Topic")

            if add_topic_submitted:
                if not new_topic_title.strip():
                    st.error("Topic can't be empty.")
                else:
                    add_task(user_id, new_topic_title, new_topic_date.isoformat(), goal["id"])
                    st.success(f"Added '{new_topic_title.strip()}'.")
                    st.rerun()


def _render_readonly_task_summary(user_id: int, goal_id: int) -> None:
    """
    A plain view-only status list for the Dashboard -- no checkboxes,
    no buttons. Actually managing tasks (check off, reschedule, add,
    extend) only happens on the Goals & Tasks page.
    """
    all_tasks = get_tasks_for_goal(user_id, goal_id)
    with st.expander(f"📋 {len(all_tasks)} topics/tasks"):
        if not all_tasks:
            st.caption("No topics yet.")
        else:
            for task in all_tasks:
                icon = "✅" if task["is_done"] else "⬜"
                task_date_str = task["task_date"] if isinstance(task["task_date"], str) else str(task["task_date"])
                st.caption(f"{icon} {task_date_str} · {task['title']}")
        st.page_link("pages/4_Goals_Tasks.py", label="Manage this goal →", icon="🎯")


def _render_manageable_task_row(
    user_id: int, task: dict, subject_names: list[str], subject_lookup: dict, context_key: str, goal_id: int
) -> None:
    row_key = f"{context_key}_{task['id']}"
    pending_key = f"pending_complete_{row_key}"
    reschedule_key = f"show_reschedule_{row_key}"

    was_done = bool(task["is_done"])
    task_date_str = task["task_date"] if isinstance(task["task_date"], str) else str(task["task_date"])
    is_future = not was_done and date.fromisoformat(task_date_str) > date.today()

    if is_future:
        col_check, col_title, col_today, col_reschedule, col_delete = st.columns([1, 3, 1, 1, 1])
    else:
        col_check, col_title, col_reschedule, col_delete = st.columns([1, 4, 1, 1])
        col_today = None

    new_done = col_check.checkbox("", value=was_done, key=f"check_{row_key}")

    label = f"{task_date_str} · {task['title']}"
    if was_done:
        col_title.markdown(f"~~{label}~~")
    else:
        col_title.write(label)

    if col_today is not None and col_today.button("⏩", key=f"pull_{row_key}", help="Do this today instead"):
        result = pull_task_forward(user_id, goal_id, task["id"])
        if result["shifted"]:
            msg = "Moved to today."
            if result["new_end_date"]:
                msg += f" Goal now finishes {result['new_end_date']}."
            st.success(msg)
        st.rerun()

    if col_reschedule.button("📅", key=f"resched_btn_{row_key}", help="Reschedule this task"):
        st.session_state[reschedule_key] = not st.session_state.get(reschedule_key, False)

    if col_delete.button("🗑️", key=f"del_{row_key}"):
        delete_task(user_id, task["id"])
        st.rerun()

    # Just unticked a completed task -- undo it (and remove the study
    # session that was auto-logged when it was completed).
    if was_done and not new_done:
        uncomplete_task(user_id, task["id"])
        st.rerun()

    # Just ticked an incomplete task -- ask how long/which subject first.
    if not was_done and new_done:
        st.session_state[pending_key] = True

    if st.session_state.get(pending_key):
        with st.container(border=True):
            st.caption(f"Mark **{task['title']}** complete")

            no_subject = st.checkbox(
                "Just mark it done -- don't log study time for a subject",
                key=f"no_subject_{row_key}",
            )

            if no_subject:
                if st.button("✅ Mark Complete", key=f"quick_complete_{row_key}"):
                    toggle_task(user_id, task["id"], True)
                    del st.session_state[pending_key]
                    st.balloons()
                    st.success("Marked complete.")
                    st.rerun()
            elif not subject_names:
                st.warning("Add a subject on the Study page first, or tick the box above.")
            else:
                default_minutes = 30
                if task.get("planned_start_time") and task.get("planned_end_time"):
                    try:
                        sh, sm = map(int, task["planned_start_time"].split(":"))
                        eh, em = map(int, task["planned_end_time"].split(":"))
                        computed = (eh * 60 + em) - (sh * 60 + sm)
                        if computed > 0:
                            default_minutes = computed
                    except (ValueError, AttributeError):
                        pass

                with st.form(f"complete_form_{row_key}"):
                    subject_choice = st.selectbox("Subject", subject_names, key=f"subj_{row_key}")
                    minutes_spent = duration_input(
                        "Time studied", key=f"complete_dur_{row_key}", default_minutes=default_minutes
                    )
                    notes_input = st.text_input("Notes", value=task["title"], key=f"note_{row_key}")
                    confirm_col, cancel_col = st.columns(2)
                    confirmed = confirm_col.form_submit_button("✅ Save & Complete")
                    cancelled = cancel_col.form_submit_button("Cancel")

                if confirmed:
                    complete_task_with_session(
                        user_id=user_id,
                        task_id=task["id"],
                        subject_id=subject_lookup[subject_choice],
                        duration_minutes=minutes_spent,
                        task_date=task_date_str,
                        notes=notes_input,
                    )
                    del st.session_state[pending_key]
                    st.balloons()
                    st.success(f"Logged {minutes_spent} min of {subject_choice}.")
                    st.rerun()
                if cancelled:
                    del st.session_state[pending_key]
                    st.rerun()

    if st.session_state.get(reschedule_key):
        with st.container(border=True):
            new_date = st.date_input(
                "Move to", value=date.fromisoformat(task_date_str), key=f"new_date_{row_key}"
            )
            if st.button("Confirm Reschedule", key=f"confirm_resched_{row_key}"):
                reschedule_task(user_id, task["id"], new_date.isoformat())
                del st.session_state[reschedule_key]
                st.success(f"Moved to {new_date.strftime('%d %b %Y')}.")
                st.rerun()
