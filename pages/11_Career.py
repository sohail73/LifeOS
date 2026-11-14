"""
pages/11_Career.py

Career planning, in six parts:

1. Roadmap -- your learning path as a flowchart: a sequence of steps
   (e.g. Data Science, then DL, then MLOps, then Cloud Computing,
   then AWS, then LLM, then RAG), each Ready (done) / In Progress
   (running) / Future (not started), reorderable, and linkable to a
   goal -- once that goal hits 100%, the step auto-promotes to Ready.

2. Job Roles -- the jobs you want to be ready for (Data Scientist, AI Engineer...).
   Attach the roadmap steps each role needs; the role turns "Ready" on its own
   once all of its steps are Ready, drawn as a flow: steps -> role.

3. Reward Ladder -- a personal "once I reach X, I'll do/get Y" list,
   e.g. milestone salary figures paired with what you'll do once you
   hit them. Sorted by the milestone's numeric value where given, so
   it reads top to bottom as a ladder.

4. Job Targets -- which job(s) you're aiming for: Ready (you're
   qualified now), In Progress (actively working toward it -- link
   one or more long-term goals; once every linked goal hits 100%, it
   auto-promotes to Ready), Future (something you'll go for later),
   or Achieved (you got it). Give a job a deadline ("crack this by
   30 Jan") to see a countdown, and mark it Achieved any time --
   before or after the deadline -- once you land it.

5. Notes -- a free-form career scratchpad.

6. Future Topics -- a "someday/maybe" study wishlist (moved here from
   the Study page, since it's really about what's next for your
   career/learning rather than day-to-day studying).
"""

from datetime import date

import streamlit as st

from analytics.goal_maintenance import (
    auto_advance_roadmap_lanes,
    auto_promote_ready_jobs,
    auto_promote_ready_roadmap_steps,
    job_role_readiness,
    job_target_progress_pct,
    roadmap_step_progress_pct,
)
from analytics.tasks_analytics import goal_progress
from auth.session import current_user_id, current_user_name, require_login
from config.constants import JOB_TARGET_STATUSES, ROADMAP_STEP_STATUSES
from database.queries import (
    add_career_note,
    add_future_topic,
    add_job_role,
    add_job_target,
    add_reward_milestone,
    add_roadmap_step,
    delete_career_note,
    delete_future_topic,
    delete_job_role,
    delete_job_target,
    delete_reward_milestone,
    delete_roadmap_step,
    get_avatar_base64,
    get_career_notes,
    get_future_topics,
    get_job_roles,
    get_job_targets,
    get_linked_goals_for_job_target,
    get_linked_goals_for_roadmap_step,
    get_long_term_goals,
    get_reward_milestones,
    get_roadmap_steps,
    get_tasks_df,
    link_job_target_goal,
    link_roadmap_step_goal,
    mark_job_target_achieved,
    move_roadmap_step,
    set_job_role_steps,
    set_job_target_pinned,
    toggle_career_note,
    toggle_reward_milestone,
    unlink_job_target_goal,
    unlink_roadmap_step_goal,
    update_career_note,
    update_job_role,
    update_job_target,
    update_reward_milestone,
    update_roadmap_step,
)
from utils.ui import (
    job_board_html,
    job_roles_flow_html,
    kpi_card_row,
    page_header,
    progress_bar_html,
    render_sidebar_branding,
    reward_ladder_html,
    roadmap_flowchart_html,
    status_badge,
)

st.set_page_config(page_title="Career - LifeOS", page_icon="⚡", layout="wide")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
page_header("Career", eyebrow="Roadmap and targets")
st.caption("Your learning roadmap, your reward ladder, and the jobs you're aiming for.")

promoted_jobs = auto_promote_ready_jobs(user_id)
for title in promoted_jobs:
    st.toast(f"'{title}' is complete -- moved to Ready!")

roadmap_tab, roles_tab, rewards_tab, jobs_tab, notes_tab, future_topics_tab = st.tabs(
    ["Roadmap", "Job Roles", "Reward Ladder", "Job Targets", "Notes", "Future Topics"]
)

# ---------------------------------------------------------------------------
# Roadmap -- a sequential learning path shown as a flowchart
# ---------------------------------------------------------------------------
with roadmap_tab:
    st.subheader("Your Learning Roadmap")
    st.caption(
        "The order you're learning things in -- e.g. Data Science, then DL, then MLOps, "
        "then Cloud Computing, then AWS, then LLM, then RAG. Each step is Ready (done), "
        "In Progress (running), or Future (not started yet), and can be linked to a goal -- "
        "once that goal is 100% complete, the step auto-promotes to Ready. Learning two "
        "things at once (say Data Science and Java)? Put them on separate tracks: they show "
        "side by side, and when a step finishes only its own track moves on to the next "
        "step -- the other track keeps running in parallel. Inside a track, steps that share "
        "the same Step number run in parallel too (say FastAPI and Cloud both as Step 4): "
        "they stack one below the other, with arrows from the step before them and on to the "
        "step after them. The next step starts once all of them are Ready."
    )

    promoted_steps = auto_promote_ready_roadmap_steps(user_id)
    for title in promoted_steps:
        st.toast(f"'{title}' is complete -- moved to Ready!")
    for title in auto_advance_roadmap_lanes(user_id):
        st.toast(f"Next up on its track: '{title}' is now In Progress.")

    all_goals_for_roadmap = get_long_term_goals(user_id)
    steps = get_roadmap_steps(user_id)

    if not steps:
        st.info("Nothing here yet. Add your first step below.")
    else:
        flow_items = []
        for s in steps:
            linked = get_linked_goals_for_roadmap_step(user_id, s["id"])
            flow_items.append(
                {
                    "order_index": s["order_index"],
                    "title": s["title"],
                    "status": s["status"],
                    "lane": s["lane"],
                    "progress_pct": roadmap_step_progress_pct(user_id, s),
                    "goal_titles": [g["title"] for g in linked],
                }
            )
        roadmap_flowchart_html(flow_items)

        st.divider()
        st.markdown("**Manage steps**")
        for step in steps:
            lane_stages = sorted({x["order_index"] for x in steps if x["lane"] == step["lane"]})
            lane_pos = lane_stages.index(step["order_index"])
            edit_key = f"editing_step_{step['id']}"
            links_key = f"editing_step_links_{step['id']}"
            linked_goals = get_linked_goals_for_roadmap_step(user_id, step["id"])

            with st.container(border=True):
                title_col, status_col, up_col, down_col, edit_col, delete_col = st.columns([3, 2, 1, 1, 1, 1])
                title_col.markdown(f"**Track {step['lane']} · Step {step['order_index']}: {step['title']}**")
                status_col.markdown(status_badge(step["status"]), unsafe_allow_html=True)

                if up_col.button("Move up", key=f"up_step_{step['id']}", disabled=(lane_pos == 0),
                                 help="Moves this step's whole stage (all steps with the same Step number)."):
                    move_roadmap_step(user_id, step["id"], "up")
                    st.rerun()
                if down_col.button("Move down", key=f"down_step_{step['id']}", disabled=(lane_pos == len(lane_stages) - 1),
                                   help="Moves this step's whole stage (all steps with the same Step number)."):
                    move_roadmap_step(user_id, step["id"], "down")
                    st.rerun()
                if edit_col.button("Edit", key=f"edit_step_btn_{step['id']}"):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                if delete_col.button("Delete", key=f"del_step_{step['id']}"):
                    delete_roadmap_step(user_id, step["id"])
                    st.rerun()

                if step["notes"]:
                    st.write(step["notes"])
                if linked_goals:
                    st.caption("Tracked by: " + ", ".join(g["title"] for g in linked_goals))

                if st.button("Manage linked goals", key=f"step_links_btn_{step['id']}"):
                    st.session_state[links_key] = not st.session_state.get(links_key, False)

                if st.session_state.get(links_key):
                    with st.container(border=True):
                        st.markdown("**Linked goals** (optional -- for 'In Progress')")
                        if not linked_goals:
                            st.caption("None yet.")
                        for g in linked_goals:
                            gc1, gc2 = st.columns([5, 1])
                            gc1.write(g["title"])
                            if gc2.button("Remove", key=f"unlink_step_goal_{step['id']}_{g['id']}"):
                                unlink_roadmap_step_goal(user_id, step["id"], g["id"])
                                st.rerun()

                        available_goals = [
                            g for g in all_goals_for_roadmap if g["id"] not in {lg["id"] for lg in linked_goals}
                        ]
                        if available_goals:
                            gcol1, gcol2 = st.columns([4, 1])
                            new_goal_label = gcol1.selectbox(
                                "Add a goal", [g["title"] for g in available_goals],
                                key=f"add_step_goal_select_{step['id']}", label_visibility="collapsed",
                            )
                            if gcol2.button("Add", key=f"add_step_goal_btn_{step['id']}"):
                                chosen = next(g for g in available_goals if g["title"] == new_goal_label)
                                link_roadmap_step_goal(user_id, step["id"], chosen["id"])
                                st.rerun()

                if st.session_state.get(edit_key):
                    with st.form(f"edit_step_form_{step['id']}"):
                        e_title = st.text_input("Step title", value=step["title"])
                        e_status = st.selectbox(
                            "Status", ROADMAP_STEP_STATUSES, index=ROADMAP_STEP_STATUSES.index(step["status"])
                        )
                        e_lane = st.number_input(
                            "Track number (steps on different tracks run in parallel)",
                            min_value=1, value=int(step["lane"]), step=1,
                        )
                        e_order = st.number_input(
                            "Step number (steps with the same number in a track run in parallel)",
                            min_value=1, value=int(step["order_index"]), step=1,
                        )
                        e_notes = st.text_area("Notes", value=step["notes"] or "")
                        save_edit = st.form_submit_button("Save Changes", use_container_width=True)

                    if save_edit:
                        # Moving to another track without touching the number = "add at the end there".
                        keep_end_of_new_lane = int(e_lane) != step["lane"] and int(e_order) == step["order_index"]
                        update_roadmap_step(
                            user_id, step["id"], title=e_title, status=e_status, notes=e_notes,
                            lane=int(e_lane), order_index=None if keep_end_of_new_lane else int(e_order),
                        )
                        del st.session_state[edit_key]
                        st.success("Step updated.")
                        st.rerun()

    st.divider()
    st.subheader("Add a Step")
    st.caption(
        "New steps are added to the end of the chosen track -- reorder them with Move up/down above. "
        "Pick \"New parallel track\" to start a second chain that runs alongside the others. "
        "To run a step in parallel with another one in the same track, give it the same Step number."
    )
    existing_lanes = sorted({x["lane"] for x in steps})
    next_lane = (max(existing_lanes) + 1) if existing_lanes else 1
    lane_choices = {f"Track {n}": n for n in existing_lanes}
    lane_choices[f"New parallel track (Track {next_lane})"] = next_lane
    with st.form("add_step_form"):
        s_title = st.text_input("Step title", placeholder="e.g. Data Science / Deep Learning / MLOps / AWS / RAG")
        s_lane_label = st.selectbox("Track", list(lane_choices.keys()), key="new_step_lane")
        s_order = st.number_input(
            "Step number (0 = add after the last step; same number as an existing step = run in parallel with it)",
            min_value=0, value=0, step=1, key="new_step_order",
        )
        s_status = st.selectbox("Status", ROADMAP_STEP_STATUSES, key="new_step_status")
        s_notes = st.text_area("Notes (optional)")
        s_submitted = st.form_submit_button("Add Step", use_container_width=True)

    if s_submitted:
        if not s_title.strip():
            st.error("Step title can't be empty.")
        else:
            add_roadmap_step(
                user_id, title=s_title, status=s_status, notes=s_notes,
                lane=lane_choices[s_lane_label], order_index=int(s_order) or None,
            )
            st.success(f"Added: {s_title.strip()}")
            st.rerun()

# ---------------------------------------------------------------------------
# Job roles -- roles you want to be ready for, built from roadmap steps
# ---------------------------------------------------------------------------
with roles_tab:
    st.subheader("Job Roles")
    st.caption(
        "The jobs you want to be ready for -- Data Scientist, AI Engineer, whatever you like. Attach the "
        "roadmap steps each role needs. You don't tick anything: once every attached step is Ready, the "
        "role turns Ready by itself. A step can feed several roles (Python helps both)."
    )

    # (the roadmap tab above already promoted any finished steps, so this reads fresh statuses)
    roadmap_steps_now = get_roadmap_steps(user_id)
    step_labels = {x["id"]: f"Track {x['lane']} · Step {x['order_index']}: {x['title']}" for x in roadmap_steps_now}
    step_ids = list(step_labels.keys())
    roles = get_job_roles(user_id)

    if not roadmap_steps_now:
        st.info("Add some steps on the Roadmap tab first -- then you can attach them to your job roles here.")

    if not roles:
        st.info("No job roles yet. Add your first one below.")
    else:
        role_data = [dict(r, **job_role_readiness(user_id, r)) for r in roles]
        kpi_card_row([
            {"label": "Job roles", "value": len(role_data), "color": "indigo"},
            {"label": "Ready", "value": sum(1 for r in role_data if r["status"] == "Ready"), "color": "green"},
            {"label": "In Progress", "value": sum(1 for r in role_data if r["status"] == "In Progress"), "color": "teal"},
        ])
        job_roles_flow_html(role_data)

        st.divider()
        st.markdown("**Manage job roles**")
        for role in role_data:
            edit_key = f"editing_role_{role['id']}"
            with st.container(border=True):
                title_col, status_col, edit_col, delete_col = st.columns([3, 2, 1, 1])
                title_col.markdown(f"**{role['title']}**")
                status_col.markdown(status_badge(role["status"]), unsafe_allow_html=True)
                if edit_col.button("Edit", key=f"edit_role_btn_{role['id']}"):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                if delete_col.button("Delete", key=f"del_role_{role['id']}"):
                    delete_job_role(user_id, role["id"])
                    st.rerun()

                if role["notes"]:
                    st.write(role["notes"])
                if role["total"]:
                    st.caption(f"{role['ready_count']} of {role['total']} steps ready · {role['pct']:.0f}% there")

                attached_ids = [x["id"] for x in role["steps"]]
                chosen = st.multiselect(
                    "Roadmap steps this role needs", step_ids, default=attached_ids,
                    format_func=lambda sid: step_labels.get(sid, str(sid)), key=f"role_steps_{role['id']}",
                    disabled=not step_ids,
                )
                if st.button("Save steps", key=f"save_role_steps_{role['id']}", disabled=set(chosen) == set(attached_ids)):
                    set_job_role_steps(user_id, role["id"], chosen)
                    st.rerun()

                if st.session_state.get(edit_key):
                    with st.form(f"edit_role_form_{role['id']}"):
                        e_title = st.text_input("Role", value=role["title"])
                        e_notes = st.text_area("Notes", value=role["notes"] or "")
                        save_edit = st.form_submit_button("Save Changes", use_container_width=True)
                    if save_edit:
                        if not e_title.strip():
                            st.error("Role can't be empty.")
                        else:
                            update_job_role(user_id, role["id"], e_title, e_notes)
                            del st.session_state[edit_key]
                            st.success("Role updated.")
                            st.rerun()

    st.divider()
    st.subheader("Add a Job Role")
    with st.form("add_role_form"):
        r_title = st.text_input("Role", placeholder="e.g. Data Scientist / AI Engineer / Backend Developer")
        r_steps = st.multiselect(
            "Roadmap steps this role needs (optional -- you can attach them later)", step_ids,
            format_func=lambda sid: step_labels.get(sid, str(sid)), disabled=not step_ids,
        )
        r_notes = st.text_area("Notes (optional)")
        r_submitted = st.form_submit_button("Add Role", use_container_width=True)
    if r_submitted:
        if not r_title.strip():
            st.error("Role can't be empty.")
        else:
            new_role_id = add_job_role(user_id, r_title, r_notes)
            if r_steps:
                set_job_role_steps(user_id, new_role_id, r_steps)
            st.success(f"Added: {r_title.strip()}")
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
        unlocked = sum(1 for r in rewards if r["is_achieved"])
        next_reward = next((r for r in rewards if not r["is_achieved"]), None)
        progress_bar_html(round(unlocked / len(rewards) * 100, 1), label=f"{unlocked} of {len(rewards)} rewards unlocked")
        if next_reward:
            st.markdown(f"**Next up:** {next_reward['milestone_label']} &rarr; {next_reward['reward_description']}",
                        unsafe_allow_html=True)
        else:
            st.success("Every reward on the ladder is unlocked.")
        reward_ladder_html(rewards)

        st.divider()
        st.markdown("**Manage milestones** -- tick the box when you've reached one")
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
        board_jobs = [dict(j, progress_pct=job_target_progress_pct(user_id, j)) for j in jobs]
        today_ = date.today()
        open_jobs = [j for j in jobs if j["status"] != "Achieved" and j["deadline"]]
        upcoming = sorted((j for j in open_jobs if date.fromisoformat(j["deadline"]) >= today_), key=lambda j: j["deadline"])
        overdue_count = sum(1 for j in open_jobs if date.fromisoformat(j["deadline"]) < today_)
        next_job = upcoming[0] if upcoming else None
        next_days = (date.fromisoformat(next_job["deadline"]) - today_).days if next_job else None
        deadline_sub = next_job["title"] if next_job else ("no upcoming deadlines" if open_jobs else "no deadlines set")
        if overdue_count:
            deadline_sub += f" -- {overdue_count} overdue"
        kpi_card_row([
            {"label": "In Progress", "value": sum(1 for j in jobs if j["status"] == "In Progress"), "color": "indigo"},
            {"label": "Ready", "value": sum(1 for j in jobs if j["status"] == "Ready"), "color": "green"},
            {"label": "Achieved", "value": sum(1 for j in jobs if j["status"] == "Achieved"), "color": "green"},
            {
                "label": "Next deadline",
                "value": f"{next_days}d" if next_job else "--",
                "sub": deadline_sub,
                "color": "amber" if overdue_count or (next_job and next_days <= 30) else "teal",
            },
        ])
        job_board_html(board_jobs)

        st.divider()
        st.markdown("**Manage job targets**")
        status_filter = st.selectbox("Filter by status", ["All"] + JOB_TARGET_STATUSES, key="job_status_filter")
        visible_jobs = jobs if status_filter == "All" else [j for j in jobs if j["status"] == status_filter]

        if not visible_jobs:
            st.caption(f"Nothing with status '{status_filter}'.")

        for job in visible_jobs:
            edit_key = f"editing_job_{job['id']}"
            links_key = f"editing_job_links_{job['id']}"
            linked_goals = get_linked_goals_for_job_target(user_id, job["id"])

            with st.container(border=True):
                title_col, status_col, edit_col, delete_col = st.columns([3, 2, 1, 1])
                company_text = f" -- {job['company']}" if job["company"] else ""
                package_text = f" ({job['target_package']})" if job["target_package"] else ""
                title_col.markdown(f"**{job['title']}{company_text}{package_text}**")
                status_col.markdown(status_badge(job["status"]), unsafe_allow_html=True)

                if edit_col.button("Edit", key=f"edit_job_btn_{job['id']}"):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                if delete_col.button("Delete", key=f"del_job_{job['id']}"):
                    delete_job_target(user_id, job["id"])
                    st.rerun()

                achieve_col, pin_col, _spacer = st.columns([1, 2, 3])
                if job["status"] != "Achieved":
                    if achieve_col.button("Got it!", key=f"achieve_job_{job['id']}"):
                        mark_job_target_achieved(user_id, job["id"])
                        st.rerun()
                if job["is_pinned"]:
                    if pin_col.button("Unpin from Dashboard", key=f"unpin_job_{job['id']}"):
                        set_job_target_pinned(user_id, job["id"], False)
                        st.rerun()
                else:
                    if pin_col.button("Pin to Dashboard", key=f"pin_job_{job['id']}"):
                        set_job_target_pinned(user_id, job["id"], True)
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
                        e_package = st.text_input("Package/CTC target (optional)", value=job["target_package"] or "", placeholder="e.g. 5 LPA")
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
                            target_package=e_package,
                        )
                        del st.session_state[edit_key]
                        st.success("Job target updated.")
                        st.rerun()

    st.divider()
    st.subheader("Add a Job Target")
    with st.form("add_job_form"):
        j_title = st.text_input("Job title", placeholder="e.g. Data Analyst / Backend Developer")
        j_company = st.text_input("Company (optional)", placeholder="e.g. TCS, or leave blank for any")
        j_package = st.text_input("Package/CTC target (optional)", placeholder="e.g. 5 LPA")
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
                target_package=j_package,
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

# ---------------------------------------------------------------------------
# Future Topics -- a "someday/maybe" study wishlist
# ---------------------------------------------------------------------------
with future_topics_tab:
    st.subheader("What I Want to Study in the Future")
    st.caption(
        "A running list of topics/subjects you want to get to eventually -- not tied to any "
        "date or goal yet. When you're ready to actually schedule one, turn it into a Long-Term "
        "Goal on the Goals & Tasks page, or add it as a step on your Roadmap above."
    )

    future_topics = get_future_topics(user_id)

    if not future_topics:
        st.caption("Nothing on your list yet -- add your first idea below.")
    else:
        for topic in future_topics:
            with st.container(border=True):
                title_col, delete_col = st.columns([5, 1])
                title_col.markdown(f"**🔮 {topic['title']}**")
                if topic["notes"]:
                    title_col.caption(topic["notes"])
                if delete_col.button("🗑️", key=f"del_future_{topic['id']}"):
                    delete_future_topic(user_id, topic["id"])
                    st.rerun()

    st.divider()
    with st.form("add_future_topic_form"):
        new_future_title = st.text_input("Topic", placeholder="e.g. Kubernetes basics, Rust ownership model")
        new_future_notes = st.text_area("Notes (optional)", placeholder="Why you want to learn this, resources, etc.")
        add_future_submitted = st.form_submit_button("Add to List", use_container_width=True)

    if add_future_submitted:
        if not new_future_title.strip():
            st.error("Topic can't be empty.")
        else:
            add_future_topic(user_id, new_future_title, new_future_notes)
            st.success(f"Added '{new_future_title.strip()}' to your future topics.")
            st.rerun()
