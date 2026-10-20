"""
widgets/task_widgets.py

Shared "task checklist" row, used both on the Goals & Tasks page
(full controls: reschedule, delete) and the Dashboard (compact: just
see and check off what's due today, so it's visible the moment you
land on the app). Both share the same completion popup (duration +
subject), which logs a real study session -- see
database.queries.complete_task_with_session.
"""

from datetime import date

import streamlit as st

from database.queries import (
    complete_task_with_session,
    delete_task,
    reschedule_task,
    set_task_priority,
    toggle_task,
    uncomplete_task,
)
from utils.ui import duration_input, priority_badge


def render_task_checklist(
    user_id: int,
    tasks: list[dict],
    subject_names: list[str],
    subject_lookup: dict,
    key_prefix: str,
    task_date: date,
    compact: bool = False,
) -> None:
    """
    compact=True (Dashboard) shows just a checkbox + title (with a
    priority badge, so you can see at a glance what to do first) --
    no reschedule/delete/priority-change controls, keeping those
    management actions on the Goals & Tasks page as the single place
    to manage tasks. Tasks are always passed in already sorted by
    priority (see database.queries.get_tasks_for_date), so this
    function doesn't re-sort them.

    Order within a priority tier comes from each goal's position (set
    once with Up/Down on the goal card in Goals & Tasks), so there are
    no per-task reorder buttons here.
    """
    if not tasks:
        st.caption("No tasks for this date.")
        return

    priority_options = {"High": 1, "Medium": 2, "Low": 3}
    priority_labels = {1: "High", 2: "Medium", 3: "Low"}

    for task in tasks:
        row_key = f"{key_prefix}_{task['id']}"
        pending_key = f"pending_complete_{row_key}"
        reschedule_key = f"show_reschedule_{row_key}"

        was_done = bool(task["is_done"])
        priority = task.get("priority", 2)

        if compact:
            col_check, col_title = st.columns([1, 6])
            col_priority = col_reschedule = col_delete = None
        else:
            col_check, col_title, col_priority, col_reschedule, col_delete = st.columns([1, 3, 2, 1, 1])

        new_done = col_check.checkbox("", value=was_done, key=f"check_{row_key}")

        label = task["title"]
        if task.get("planned_start_time") and task.get("planned_end_time"):
            label += f"  ·  🕐 {task['planned_start_time']}–{task['planned_end_time']}"
        if task.get("goal_title"):
            label += f"  ·  🏁 {task['goal_title']}"

        if was_done:
            col_title.markdown(f"~~{label}~~")
        elif compact:
            # Badge goes on the SAME line as the title (not a separate
            # markdown call below it), so it sits beside the text
            # instead of wrapping onto its own row underneath.
            col_title.markdown(f"{label} &nbsp; {priority_badge(priority)}", unsafe_allow_html=True)
        else:
            col_title.write(label)

        if not compact:
            if task.get("goal_id"):
                # Priority is inherited from the goal (set once there,
                # not per day) -- show it read-only here, change it on
                # the goal itself to affect every task under it.
                col_priority.markdown(priority_badge(priority), unsafe_allow_html=True)
            else:
                new_priority_label = col_priority.selectbox(
                    "Priority", ["High", "Medium", "Low"],
                    index=["High", "Medium", "Low"].index(priority_labels.get(priority, "Medium")),
                    key=f"priority_{row_key}", label_visibility="collapsed",
                )
                if priority_options[new_priority_label] != priority:
                    set_task_priority(user_id, task["id"], priority_options[new_priority_label])
                    st.rerun()

        if col_reschedule is not None and col_reschedule.button(
            "📅", key=f"resched_btn_{row_key}", help="Reschedule this task"
        ):
            st.session_state[reschedule_key] = not st.session_state.get(reschedule_key, False)

        if col_delete is not None and col_delete.button("🗑️", key=f"del_task_{row_key}"):
            delete_task(user_id, task["id"])
            st.rerun()

        # Just unticked a completed task -- undo it (and remove the
        # study session that was auto-logged when it was completed).
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
                            task_date=task_date.isoformat(),
                            notes=notes_input,
                        )
                        del st.session_state[pending_key]
                        st.balloons()
                        st.success(f"Logged {minutes_spent} min of {subject_choice}.")
                        st.rerun()
                    if cancelled:
                        del st.session_state[pending_key]
                        st.rerun()

        if not compact and st.session_state.get(reschedule_key):
            with st.container(border=True):
                new_date = st.date_input("Move to", value=task_date, key=f"new_date_{row_key}")
                if st.button("Confirm Reschedule", key=f"confirm_resched_{row_key}"):
                    reschedule_task(user_id, task["id"], new_date.isoformat())
                    del st.session_state[reschedule_key]
                    st.success(f"Moved to {new_date.strftime('%d %b %Y')}.")
                    st.rerun()
