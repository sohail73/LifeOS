"""
pages/11_Career.py

Career planning, in three parts:

1. Roadmap -- a timeline of targets you're aiming for: an internship,
   placement, hackathon, competition, or job, each with an optional
   target date and a status (Upcoming / Achieved).

2. Reward Ladder -- a personal "once I reach X, I'll do/get Y" list,
   e.g. milestone salary figures paired with what you'll do once you
   hit them. Sorted by the milestone's numeric value where given, so
   it reads top to bottom as a ladder.

3. Job Targets -- which job(s) you're aiming for: Ready (you're
   qualified now), In Progress (actively working toward it -- link
   one or more long-term goals; once every linked goal hits 100%, it
   auto-promotes to Ready), Future (something you'll go for later),
   or Achieved (you got it). Give a job a deadline ("crack this by
   30 Jan") to see a countdown, and mark it Achieved any time --
   before or after the deadline -- once you land it.
"""

from datetime import date

import streamlit as st

from analytics.goal_maintenance import auto_promote_ready_jobs
from analytics.tasks_analytics import goal_progress
from auth.session import current_user_id, current_user_name, require_login
from config.constants import CAREER_MILESTONE_STATUSES, CAREER_MILESTONE_TYPES, JOB_TARGET_STATUSES
from database.queries import (
    add_career_milestone,
    add_career_note,
    add_job_target,
    add_reward_milestone,
    delete_career_milestone,
    delete_career_note,
    delete_job_target,
    delete_reward_milestone,
    get_avatar_base64,
    get_career_milestones,
    get_career_notes,
    get_job_targets,
    get_linked_goals_for_job_target,
    get_long_term_goals,
    get_reward_milestones,
    get_tasks_df,
    link_job_target_goal,
    mark_job_target_achieved,
    toggle_career_note,
    toggle_reward_milestone,
    unlink_job_target_goal,
    update_career_milestone,
    update_career_note,
    update_job_target,
    update_reward_milestone,
)
from utils.ui import progress_bar_html, render_sidebar_branding, status_badge

st.set_page_config(page_title="Career - LifeOS", page_icon="⚡", layout="wide")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
st.title("Career")
st.caption("Your roadmap, your reward ladder, and the jobs you're aiming for.")

promoted_jobs = auto_promote_ready_jobs(user_id)
for title in promoted_jobs:
    st.toast(f"'{title}' is complete -- moved to Ready!")

roadmap_tab, rewards_tab, jobs_tab, notes_tab = st.tabs(["Roadmap", "Reward Ladder", "Job Targets", "Notes"])

# ---------------------------------------------------------------------------
# Roadmap
# ---------------------------------------------------------------------------
with roadmap_tab:
    st.subheader("Your Roadmap")
    st.caption(
        "Targets you're working toward -- an internship, placement, hackathon, "
        "competition, or job -- each with an optional target date."
    )

    milestones = get_career_milestones(user_id)

    if not milestones:
        st.info("Nothing here yet. Add your first target below.")
    else:
        type_filter = st.selectbox("Filter by type", ["All"] + CAREER_MILESTONE_TYPES, key="roadmap_type_filter")
        visible = (
            milestones
            if type_filter == "All"
            else [m for m in milestones if m["milestone_type"] == type_filter]
        )

        if not visible:
            st.caption(f"Nothing of type '{type_filter}'.")

        for m in visible:
            edit_key = f"editing_milestone_{m['id']}"
            with st.container(border=True):
                title_col, meta_col, edit_col, delete_col = st.columns([3, 2, 1, 1])
                title_col.markdown(f"**{m['title']}**")
                due_text = f" · target {m['target_date']}" if m["target_date"] else ""
                meta_col.markdown(
                    status_badge(m["status"]) + f" &nbsp; *{m['milestone_type']}*" + due_text,
                    unsafe_allow_html=True,
                )
                if edit_col.button("Edit", key=f"edit_milestone_btn_{m['id']}"):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                if delete_col.button("Delete", key=f"del_milestone_{m['id']}"):
                    delete_career_milestone(user_id, m["id"])
                    st.rerun()

                if m["notes"]:
                    st.caption(m["notes"])

                if st.session_state.get(edit_key):
                    with st.form(f"edit_milestone_form_{m['id']}"):
                        e_type = st.selectbox(
                            "Type", CAREER_MILESTONE_TYPES, index=CAREER_MILESTONE_TYPES.index(m["milestone_type"])
                        )
                        e_title = st.text_input("Title", value=m["title"])
                        e_has_date = st.checkbox("Has a target date", value=bool(m["target_date"]))
                        e_date = st.date_input(
                            "Target date",
                            value=date.fromisoformat(m["target_date"]) if m["target_date"] else date.today(),
                        )
                        e_status = st.selectbox(
                            "Status", CAREER_MILESTONE_STATUSES, index=CAREER_MILESTONE_STATUSES.index(m["status"])
                        )
                        e_notes = st.text_area("Notes", value=m["notes"] or "")
                        save_edit = st.form_submit_button("Save Changes", use_container_width=True)

                    if save_edit:
                        update_career_milestone(
                            user_id,
                            m["id"],
                            milestone_type=e_type,
                            title=e_title,
                            target_date=e_date.isoformat() if e_has_date else None,
                            status=e_status,
                            notes=e_notes,
                        )
                        del st.session_state[edit_key]
                        st.success("Updated.")
                        st.rerun()

    st.divider()
    st.subheader("Add a Target")
    with st.form("add_milestone_form"):
        m_type = st.selectbox("Type", CAREER_MILESTONE_TYPES, key="new_milestone_type")
        m_title = st.text_input("Title", placeholder="e.g. Summer internship / Product placement / Smart India Hackathon")
        m_has_date = st.checkbox("Set a target date")
        m_date = st.date_input("Target date", value=date.today()) if m_has_date else None
        m_notes = st.text_area("Notes (optional)")
        m_submitted = st.form_submit_button("Add", use_container_width=True)

    if m_submitted:
        if not m_title.strip():
            st.error("Title can't be empty.")
        else:
            add_career_milestone(
                user_id,
                milestone_type=m_type,
                title=m_title,
                target_date=m_date.isoformat() if m_date else None,
                status="Upcoming",
                notes=m_notes,
            )
            st.success(f"Added: {m_title.strip()}")
            st.rerun()

# ---------------------------------------------------------------------------
# Reward ladder
# ---------------------------------------------------------------------------
with rewards_tab:
    st.subheader("Reward Ladder")
    st.caption(
        "Once I reach X, I'll do Y -- e.g. '10 LPA job' paired with 'buy Abbu an iPhone', "
        "'20 LPA' with 'buy a car'. Give it a numeric value if you want it sorted like a ladder."
    )

    rewards = get_reward_milestones(user_id)

    if not rewards:
        st.info("Nothing here yet. Add your first milestone below.")
    else:
        for r in rewards:
            edit_key = f"editing_reward_{r['id']}"
            with st.container(border=True):
                check_col, text_col, edit_col, delete_col = st.columns([1, 5, 1, 1])
                achieved = check_col.checkbox(
                    "", value=bool(r["is_achieved"]), key=f"reward_check_{r['id']}", label_visibility="collapsed"
                )
                if achieved != bool(r["is_achieved"]):
                    toggle_reward_milestone(user_id, r["id"], achieved)
                    st.rerun()

                label = f"**{r['milestone_label']}** &rarr; {r['reward_description']}"
                if r["is_achieved"]:
                    text_col.markdown(f"~~{label}~~", unsafe_allow_html=True)
                else:
                    text_col.markdown(label, unsafe_allow_html=True)

                if edit_col.button("Edit", key=f"edit_reward_btn_{r['id']}"):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                if delete_col.button("Delete", key=f"del_reward_{r['id']}"):
                    delete_reward_milestone(user_id, r["id"])
                    st.rerun()

                if r["notes"]:
                    st.caption(r["notes"])

                if st.session_state.get(edit_key):
                    with st.form(f"edit_reward_form_{r['id']}"):
                        e_label = st.text_input("Milestone", value=r["milestone_label"])
                        e_value = st.number_input(
                            "Numeric value (optional, used for sorting)",
                            value=float(r["trigger_value"]) if r["trigger_value"] is not None else 0.0,
                            step=1.0,
                        )
                        e_has_value = st.checkbox("Use this numeric value for sorting", value=r["trigger_value"] is not None)
                        e_reward = st.text_area("Reward / what you'll do", value=r["reward_description"])
                        e_notes = st.text_area("Notes", value=r["notes"] or "")
                        save_edit = st.form_submit_button("Save Changes", use_container_width=True)

                    if save_edit:
                        update_reward_milestone(
                            user_id,
                            r["id"],
                            milestone_label=e_label,
                            reward_description=e_reward,
                            trigger_value=e_value if e_has_value else None,
                            notes=e_notes,
                        )
                        del st.session_state[edit_key]
                        st.success("Updated.")
                        st.rerun()

    st.divider()
    st.subheader("Add a Milestone")
    with st.form("add_reward_form"):
        r_label = st.text_input("Milestone", placeholder="e.g. 10 LPA job")
        r_has_value = st.checkbox("Give it a numeric value (so the ladder sorts correctly)")
        r_value = st.number_input("Numeric value", value=0.0, step=1.0) if r_has_value else None
        r_reward = st.text_area("Reward / what you'll do", placeholder="e.g. Buy Abbu an iPhone")
        r_notes = st.text_area("Notes (optional)")
        r_submitted = st.form_submit_button("Add", use_container_width=True)

    if r_submitted:
        if not r_label.strip() or not r_reward.strip():
            st.error("Milestone and reward can't be empty.")
        else:
            add_reward_milestone(
                user_id,
                milestone_label=r_label,
                reward_description=r_reward,
                trigger_value=r_value,
                notes=r_notes,
            )
            st.success(f"Added: {r_label.strip()}")
            st.rerun()

# ---------------------------------------------------------------------------
# Job targets
# ---------------------------------------------------------------------------
with jobs_tab:
    st.subheader("Job Targets")
    st.caption(
        "Use **Ready** for jobs you're already qualified for, **In Progress** for jobs "
        "you're actively working toward (link the goal(s) tracking your progress -- once "
        "they're all complete, it auto-promotes to Ready), **Future** for jobs you'll aim "
        "for later, and **Achieved** once you've got it. Give a job a deadline (e.g. "
        "'crack this by 30 Jan') to see how much time is left."
    )

    all_goals = get_long_term_goals(user_id)
    jobs = get_job_targets(user_id)

    def _job_countdown(deadline_str: str) -> str:
        """'X days left' / 'Deadline is today' / 'Overdue by X days' for a deadline."""
        deadline_date = date.fromisoformat(deadline_str)
        days_left = (deadline_date - date.today()).days
        if days_left > 0:
            return f"{days_left} day{'s' if days_left != 1 else ''} left"
        if days_left == 0:
            return "Deadline is today"
        return f"Overdue by {abs(days_left)} day{'s' if abs(days_left) != 1 else ''}"

    if not jobs:
        st.info("Nothing here yet. Add your first job target below.")
    else:
        status_filter = st.selectbox("Filter by status", ["All"] + JOB_TARGET_STATUSES, key="job_status_filter")
        visible_jobs = jobs if status_filter == "All" else [j for j in jobs if j["status"] == status_filter]

        if not visible_jobs:
            st.caption(f"Nothing with status '{status_filter}'.")

        for job in visible_jobs:
            edit_key = f"editing_job_{job['id']}"
            links_key = f"editing_job_links_{job['id']}"
            linked_goals = get_linked_goals_for_job_target(user_id, job["id"])

            with st.container(border=True):
                title_col, status_col, achieve_col, edit_col, delete_col = st.columns([3, 2, 2, 1, 1])
                company_text = f" -- {job['company']}" if job["company"] else ""
                title_col.markdown(f"**{job['title']}{company_text}**")
                status_col.markdown(status_badge(job["status"]), unsafe_allow_html=True)

                if job["status"] != "Achieved":
                    if achieve_col.button("Got it!", key=f"achieve_job_{job['id']}"):
                        mark_job_target_achieved(user_id, job["id"])
                        st.rerun()

                if edit_col.button("Edit", key=f"edit_job_btn_{job['id']}"):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                if delete_col.button("Delete", key=f"del_job_{job['id']}"):
                    delete_job_target(user_id, job["id"])
                    st.rerun()

                if job["deadline"]:
                    if job["status"] == "Achieved":
                        st.caption(f"Deadline was {job['deadline']}")
                    else:
                        st.caption(f"Deadline: {job['deadline']} · {_job_countdown(job['deadline'])}")

                if job["notes"]:
                    st.write(job["notes"])
                if linked_goals:
                    st.caption("Tracked by: " + ", ".join(g["title"] for g in linked_goals))

                    total_tasks = 0
                    completed_tasks = 0
                    for g in linked_goals:
                        g_tasks_df = get_tasks_df(user_id, goal_id=g["id"])
                        g_progress = goal_progress(g, g_tasks_df)
                        total_tasks += g_progress["total_tasks"]
                        completed_tasks += g_progress["completed_tasks"]
                    overall_pct = round(completed_tasks / total_tasks * 100, 1) if total_tasks else 0.0
                    progress_bar_html(overall_pct, label="Progress toward Ready")

                if st.button("Manage linked goals", key=f"links_btn_{job['id']}"):
                    st.session_state[links_key] = not st.session_state.get(links_key, False)

                if st.session_state.get(links_key):
                    with st.container(border=True):
                        st.markdown("**Linked goals** (optional -- for 'In Progress')")
                        if not linked_goals:
                            st.caption("None yet.")
                        for g in linked_goals:
                            gc1, gc2 = st.columns([5, 1])
                            gc1.write(g["title"])
                            if gc2.button("Remove", key=f"unlink_job_goal_{job['id']}_{g['id']}"):
                                unlink_job_target_goal(user_id, job["id"], g["id"])
                                st.rerun()

                        available_goals = [g for g in all_goals if g["id"] not in {lg["id"] for lg in linked_goals}]
                        if available_goals:
                            gcol1, gcol2 = st.columns([4, 1])
                            new_goal_label = gcol1.selectbox(
                                "Add a goal", [g["title"] for g in available_goals],
                                key=f"add_job_goal_select_{job['id']}", label_visibility="collapsed",
                            )
                            if gcol2.button("Add", key=f"add_job_goal_btn_{job['id']}"):
                                chosen = next(g for g in available_goals if g["title"] == new_goal_label)
                                link_job_target_goal(user_id, job["id"], chosen["id"])
                                st.rerun()

                if st.session_state.get(edit_key):
                    with st.form(f"edit_job_form_{job['id']}"):
                        e_title = st.text_input("Job title", value=job["title"])
                        e_company = st.text_input("Company (optional)", value=job["company"] or "")
                        e_status = st.selectbox(
                            "Status", JOB_TARGET_STATUSES, index=JOB_TARGET_STATUSES.index(job["status"])
                        )
                        e_has_deadline = st.checkbox("Has a deadline", value=bool(job["deadline"]))
                        e_deadline = st.date_input(
                            "Deadline (crack this job by...)",
                            value=date.fromisoformat(job["deadline"]) if job["deadline"] else date.today(),
                        )
                        e_notes = st.text_area("Notes", value=job["notes"] or "")
                        save_edit = st.form_submit_button("Save Changes", use_container_width=True)

                    if save_edit:
                        update_job_target(
                            user_id,
                            job["id"],
                            title=e_title,
                            company=e_company,
                            status=e_status,
                            notes=e_notes,
                            deadline=e_deadline.isoformat() if e_has_deadline else None,
                        )
                        del st.session_state[edit_key]
                        st.success("Job target updated.")
                        st.rerun()

    st.divider()
    st.subheader("Add a Job Target")
    with st.form("add_job_form"):
        j_title = st.text_input("Job title", placeholder="e.g. Data Analyst / Backend Developer")
        j_company = st.text_input("Company (optional)", placeholder="e.g. TCS, or leave blank for any")
        j_status = st.selectbox("Status", JOB_TARGET_STATUSES, key="new_job_status")
        j_has_deadline = st.checkbox("Set a deadline (crack this job by...)")
        j_deadline = st.date_input("Deadline", value=date.today()) if j_has_deadline else None
        j_linked_goal_titles = st.multiselect(
            "Link goal(s) tracking this (optional -- for 'In Progress')", [g["title"] for g in all_goals],
        )
        j_notes = st.text_area("Notes (optional)")
        j_submitted = st.form_submit_button("Add", use_container_width=True)

    if j_submitted:
        if not j_title.strip():
            st.error("Job title can't be empty.")
        else:
            new_job_id = add_job_target(
                user_id,
                title=j_title,
                company=j_company,
                status=j_status,
                notes=j_notes,
                deadline=j_deadline.isoformat() if j_deadline else None,
            )
            for g in all_goals:
                if g["title"] in j_linked_goal_titles:
                    link_job_target_goal(user_id, new_job_id, g["id"])
            st.success(f"Added: {j_title.strip()}")
            st.rerun()

# ---------------------------------------------------------------------------
# Notes (free-form scratchpad)
# ---------------------------------------------------------------------------
with notes_tab:
    st.subheader("Notes")
    st.caption(
        "Anything worth writing down so you don't forget it -- e.g. 'this job has 3-4 "
        "goals attached, but I still need to study more for it and haven't created that "
        "goal yet, do it later'. Tick a note off once it's handled."
    )

    with st.form("add_note_form"):
        n_content = st.text_area("New note", placeholder="Write anything you want to remember...")
        n_submitted = st.form_submit_button("Add Note", use_container_width=True)

    if n_submitted:
        if not n_content.strip():
            st.error("Note can't be empty.")
        else:
            add_career_note(user_id, n_content)
            st.success("Note added.")
            st.rerun()

    st.divider()

    notes = get_career_notes(user_id)
    if not notes:
        st.info("No notes yet. Add your first one above.")
    else:
        pending = [n for n in notes if not n["is_done"]]
        done = [n for n in notes if n["is_done"]]

        if pending:
            st.markdown("**To do**")
            for note in pending:
                edit_key = f"editing_note_{note['id']}"
                with st.container(border=True):
                    check_col, text_col, edit_col, delete_col = st.columns([1, 5, 1, 1])
                    checked = check_col.checkbox(
                        "", value=False, key=f"note_check_{note['id']}", label_visibility="collapsed"
                    )
                    if checked:
                        toggle_career_note(user_id, note["id"], True)
                        st.rerun()

                    text_col.write(note["content"])
                    if edit_col.button("Edit", key=f"edit_note_btn_{note['id']}"):
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                    if delete_col.button("Delete", key=f"del_note_{note['id']}"):
                        delete_career_note(user_id, note["id"])
                        st.rerun()

                    if st.session_state.get(edit_key):
                        with st.form(f"edit_note_form_{note['id']}"):
                            e_content = st.text_area("Note", value=note["content"])
                            save_edit = st.form_submit_button("Save Changes", use_container_width=True)
                        if save_edit:
                            update_career_note(user_id, note["id"], e_content)
                            del st.session_state[edit_key]
                            st.success("Note updated.")
                            st.rerun()

        if done:
            st.markdown("**Done**")
            for note in done:
                with st.container(border=True):
                    check_col, text_col, delete_col = st.columns([1, 6, 1])
                    checked = check_col.checkbox(
                        "", value=True, key=f"note_check_{note['id']}", label_visibility="collapsed"
                    )
                    if not checked:
                        toggle_career_note(user_id, note["id"], False)
                        st.rerun()

                    text_col.markdown(f"~~{note['content']}~~")
                    if delete_col.button("Delete", key=f"del_note_{note['id']}"):
                        delete_career_note(user_id, note["id"])
                        st.rerun()
