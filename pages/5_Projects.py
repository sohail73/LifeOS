"""
pages/5_Projects.py

A place to track what you want to build/become and where you stand:
- "Ready" -- you're already qualified/prepared for this, nothing more needed.
- "In Progress" -- actively working toward it; optionally link one or
  more long-term goals tracking your day-to-day progress on it. Once
  every linked goal is 100% complete, the project auto-promotes to
  "Ready" the next time this page loads (see
  analytics.goal_maintenance.auto_promote_ready_projects).
- "Planned" -- a future ambition; optionally link items from your
  Future Topics wishlist (Study page) that feed into it.
- "On Hold" / "Done" -- the usual project states.

Plus a simple "Skills I Know" tab -- a flat list, no dates or status,
just what you can already do.
"""

from datetime import date

import streamlit as st

from analytics.goal_maintenance import auto_promote_ready_projects
from auth.session import current_user_id, current_user_name, require_login
from database.queries import (
    add_known_skill,
    add_project,
    delete_known_skill,
    delete_project,
    get_avatar_base64,
    get_future_topics,
    get_known_skills,
    get_linked_future_topics_for_project,
    get_linked_goals_for_project,
    get_long_term_goals,
    get_projects,
    link_project_future_topic,
    link_project_goal,
    unlink_project_future_topic,
    unlink_project_goal,
    update_project,
)
from utils.ui import page_header, render_sidebar_branding, status_badge

st.set_page_config(page_title="Projects - LifeOS", page_icon="⚡", layout="wide")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
page_header("Projects", eyebrow="Build")
st.caption("What you want to build, what you're ready for, and what you're working toward.")

promoted = auto_promote_ready_projects(user_id)
for title in promoted:
    st.toast(f"🎉 '{title}' is complete -- moved to Ready!", icon="🎉")

STATUS_OPTIONS = ["Ready", "In Progress", "Planned", "On Hold", "Done"]
STATUS_ICONS = {"Ready": "✅", "In Progress": "🚧", "Planned": "🗓️", "On Hold": "⏸️", "Done": "🏁"}

all_goals = get_long_term_goals(user_id)
all_future_topics = get_future_topics(user_id)

list_tab, add_tab, skills_tab = st.tabs(["Your Projects", "Add a Project", "Skills I Know"])

with list_tab:
    projects = get_projects(user_id)

    if not projects:
        st.info(
            "**Nothing here yet.**\n\n"
            "Add what you're ready for, working on, or planning in the **Add a Project** tab."
        )
    else:
        status_filter = st.selectbox("Filter by status", ["All"] + STATUS_OPTIONS)
        visible_projects = (
            projects if status_filter == "All" else [p for p in projects if p["status"] == status_filter]
        )

        if not visible_projects:
            st.caption(f"Nothing with status '{status_filter}'.")

        for project in visible_projects:
            edit_key = f"editing_project_{project['id']}"
            links_key = f"editing_links_{project['id']}"
            icon = STATUS_ICONS.get(project["status"], "📌")

            linked_goals = get_linked_goals_for_project(user_id, project["id"])
            linked_topics = get_linked_future_topics_for_project(user_id, project["id"])

            with st.container(border=True):
                title_col, status_col, edit_col, delete_col = st.columns([3, 2, 1, 1])
                title_col.markdown(f"**{icon} {project['title']}**")
                due_text = f" · due {project['target_date']}" if project['target_date'] else ""
                status_col.markdown(status_badge(project["status"]) + due_text, unsafe_allow_html=True)

                if edit_col.button("✏️", key=f"edit_btn_{project['id']}", help="Edit"):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                if delete_col.button("🗑️", key=f"del_project_{project['id']}", help="Delete"):
                    delete_project(user_id, project["id"])
                    st.rerun()

                if project["tech_stack"]:
                    st.caption(f"**Tech stack:** {project['tech_stack']}")
                if project["description"]:
                    st.write(project["description"])
                if linked_goals:
                    st.caption("🏁 Tracked by: " + ", ".join(g["title"] for g in linked_goals))
                if linked_topics:
                    st.caption("🔮 Future topics: " + ", ".join(t["title"] for t in linked_topics))
                if project["notes"]:
                    st.caption(f"**Notes:** {project['notes']}")

                if st.button("🔗 Manage links", key=f"links_btn_{project['id']}"):
                    st.session_state[links_key] = not st.session_state.get(links_key, False)

                if st.session_state.get(links_key):
                    with st.container(border=True):
                        st.markdown("**Linked goals** (optional -- for 'In Progress')")
                        if not linked_goals:
                            st.caption("None yet.")
                        for g in linked_goals:
                            gc1, gc2 = st.columns([5, 1])
                            gc1.write(g["title"])
                            if gc2.button("✖", key=f"unlink_goal_{project['id']}_{g['id']}"):
                                unlink_project_goal(user_id, project["id"], g["id"])
                                st.rerun()

                        available_goals = [g for g in all_goals if g["id"] not in {lg["id"] for lg in linked_goals}]
                        if available_goals:
                            gcol1, gcol2 = st.columns([4, 1])
                            new_goal_label = gcol1.selectbox(
                                "Add a goal", [g["title"] for g in available_goals],
                                key=f"add_goal_select_{project['id']}", label_visibility="collapsed",
                            )
                            if gcol2.button("Add", key=f"add_goal_btn_{project['id']}"):
                                chosen = next(g for g in available_goals if g["title"] == new_goal_label)
                                link_project_goal(user_id, project["id"], chosen["id"])
                                st.rerun()

                        st.divider()
                        st.markdown("**Linked future topics** (optional -- for 'Planned')")
                        if not linked_topics:
                            st.caption("None yet.")
                        for t in linked_topics:
                            tc1, tc2 = st.columns([5, 1])
                            tc1.write(t["title"])
                            if tc2.button("✖", key=f"unlink_topic_{project['id']}_{t['id']}"):
                                unlink_project_future_topic(user_id, project["id"], t["id"])
                                st.rerun()

                        available_topics = [
                            t for t in all_future_topics if t["id"] not in {lt["id"] for lt in linked_topics}
                        ]
                        if available_topics:
                            tcol1, tcol2 = st.columns([4, 1])
                            new_topic_label = tcol1.selectbox(
                                "Add a future topic", [t["title"] for t in available_topics],
                                key=f"add_topic_select_{project['id']}", label_visibility="collapsed",
                            )
                            if tcol2.button("Add", key=f"add_topic_btn_{project['id']}"):
                                chosen = next(t for t in available_topics if t["title"] == new_topic_label)
                                link_project_future_topic(user_id, project["id"], chosen["id"])
                                st.rerun()

                if st.session_state.get(edit_key):
                    with st.form(f"edit_project_form_{project['id']}"):
                        e_title = st.text_input("Title", value=project["title"])
                        e_status = st.selectbox(
                            "Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(project["status"])
                        )
                        e_tech = st.text_input("Tech stack", value=project["tech_stack"] or "")
                        e_target = st.date_input(
                            "Target date (optional)",
                            value=date.fromisoformat(project["target_date"]) if project["target_date"] else None,
                        )
                        e_description = st.text_area("Description", value=project["description"] or "")
                        e_notes = st.text_area("Notes", value=project["notes"] or "")
                        save_edit = st.form_submit_button("Save Changes", use_container_width=True)

                    if save_edit:
                        update_project(
                            user_id,
                            project["id"],
                            title=e_title,
                            description=e_description,
                            status=e_status,
                            tech_stack=e_tech,
                            target_date=e_target.isoformat() if e_target else None,
                            notes=e_notes,
                        )
                        del st.session_state[edit_key]
                        st.success("Project updated.")
                        st.rerun()

with add_tab:
    st.subheader("Add Something New")
    st.caption(
        "Use **Ready** for things you're already qualified/prepared for, **In Progress** for what "
        "you're actively working toward, and **Planned** for future ambitions. Linking goals/topics "
        "is optional -- add them later from 'Manage links' if you're not sure yet."
    )

    with st.form("add_project_form"):
        title = st.text_input("Title", placeholder="e.g. Backend Developer role / Full-stack finance tracker")
        description = st.text_area("Description", placeholder="What is this? What does it involve?")
        col1, col2 = st.columns(2)
        with col1:
            status = st.selectbox("Status", STATUS_OPTIONS)
        with col2:
            has_target = st.checkbox("Set a target date")
        target_date_input = st.date_input("Target date", value=date.today()) if has_target else None

        linked_goal_titles = st.multiselect(
            "Link to goal(s) tracking this (optional)", [g["title"] for g in all_goals],
        )
        linked_topic_titles = st.multiselect(
            "Link future topic(s) that feed into this (optional)", [t["title"] for t in all_future_topics],
        )

        tech_stack = st.text_input("Tech stack / skills (optional)", placeholder="e.g. Python, Streamlit, SQLite")
        notes = st.text_area("Notes (optional)", placeholder="Anything else worth remembering")
        submitted = st.form_submit_button("Add", use_container_width=True)

    if submitted:
        if not title.strip():
            st.error("Title can't be empty.")
        else:
            new_id = add_project(
                user_id,
                title=title,
                description=description,
                status=status,
                tech_stack=tech_stack,
                target_date=target_date_input.isoformat() if target_date_input else None,
                notes=notes,
            )
            for g in all_goals:
                if g["title"] in linked_goal_titles:
                    link_project_goal(user_id, new_id, g["id"])
            for t in all_future_topics:
                if t["title"] in linked_topic_titles:
                    link_project_future_topic(user_id, new_id, t["id"])
            st.success(f"Added: {title.strip()}")
            st.rerun()

with skills_tab:
    st.subheader("Skills I Know")
    st.caption("A running list of what you can already do -- no dates, no status, just the skill.")

    skills = get_known_skills(user_id)
    if not skills:
        st.caption("Nothing here yet -- add your first skill below.")
    else:
        skill_cols = st.columns(3)
        for i, skill in enumerate(skills):
            with skill_cols[i % 3]:
                with st.container(border=True):
                    sc1, sc2 = st.columns([4, 1])
                    sc1.write(f"{skill['name']}")
                    if sc2.button("✖", key=f"del_skill_{skill['id']}"):
                        delete_known_skill(user_id, skill["id"])
                        st.rerun()

    st.divider()
    with st.form("add_skill_form"):
        new_skill = st.text_input("Skill", placeholder="e.g. Python, SQL, Public Speaking")
        add_skill_submitted = st.form_submit_button("Add Skill", use_container_width=True)

    if add_skill_submitted:
        if not new_skill.strip():
            st.error("Skill can't be empty.")
        else:
            add_known_skill(user_id, new_skill)
            st.success(f"Added: {new_skill.strip()}")
            st.rerun()
