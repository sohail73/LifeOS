"""
pages/2_Study.py

The Study module: a focus timer that auto-saves completed sessions,
manual entry as a fallback, and subject management. This is the only
module implemented in v0.1 -- see config/constants.py and
database/create_tables.py for why the architecture stays generic
enough for future modules without building them yet.
"""

from datetime import date, datetime

import streamlit as st

from auth.session import current_user_id, current_user_name, require_login
from database.queries import (
    add_future_topic,
    add_study_session,
    add_subject,
    delete_future_topic,
    delete_subject,
    get_future_topics,
    get_subject_session_count,
    get_subjects,
)
from utils.helper import format_duration
from database.queries import get_avatar_base64
from utils.ui import render_sidebar_branding, live_timer_display

st.set_page_config(page_title="Study - LifeOS", page_icon="⚡", layout="wide")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
st.title("Study")

subjects = get_subjects(user_id)
subject_names = [s["name"] for s in subjects]
subject_lookup = {s["name"]: s["id"] for s in subjects}

timer_tab, manual_tab, subjects_tab, future_tab = st.tabs(
    ["Study Timer", "Manual Entry", "Subjects", "Future Topics"]
)

# ---------------------------------------------------------------------------
# Study Timer
# ---------------------------------------------------------------------------
with timer_tab:
    st.subheader("Study Session")

    if not subject_names:
        st.warning("Add a subject in the **Subjects** tab before starting a session.")
    else:
        timer_subject = st.selectbox("Subject", subject_names, key="timer_subject")

        # Timer state lives in session_state so it survives Streamlit reruns
        # (which happen on every widget interaction) but resets per browser
        # session -- that's expected for an active, in-progress timer.
        st.session_state.setdefault("timer_running", False)
        st.session_state.setdefault("timer_start", None)
        st.session_state.setdefault("timer_elapsed_seconds", 0.0)

        def _start_timer():
            st.session_state["timer_running"] = True
            st.session_state["timer_start"] = datetime.now()

        def _pause_timer():
            if st.session_state["timer_start"] is not None:
                elapsed = (datetime.now() - st.session_state["timer_start"]).total_seconds()
                st.session_state["timer_elapsed_seconds"] += elapsed
            st.session_state["timer_running"] = False
            st.session_state["timer_start"] = None

        def _resume_timer():
            st.session_state["timer_running"] = True
            st.session_state["timer_start"] = datetime.now()

        def _stop_and_save():
            if st.session_state["timer_start"] is not None:
                elapsed = (datetime.now() - st.session_state["timer_start"]).total_seconds()
                st.session_state["timer_elapsed_seconds"] += elapsed

            total_seconds = st.session_state["timer_elapsed_seconds"]
            duration_minutes = round(total_seconds / 60, 2)

            if duration_minutes > 0:
                add_study_session(
                    user_id=user_id,
                    subject_id=subject_lookup[timer_subject],
                    date=date.today().isoformat(),
                    duration_minutes=duration_minutes,
                    source="timer",
                    start_time=None,
                    end_time=datetime.now().isoformat(),
                )
                st.session_state["last_saved_duration"] = duration_minutes

            st.session_state["timer_running"] = False
            st.session_state["timer_start"] = None
            st.session_state["timer_elapsed_seconds"] = 0.0

        # Live elapsed time. When running, show a client-side ticking
        # HH:MM:SS display (utils.ui.live_timer_display) so the screen
        # visibly counts up without needing a rerun every second. When
        # paused/stopped, a plain metric is enough since nothing is moving.
        if st.session_state["timer_running"] and st.session_state["timer_start"] is not None:
            live_timer_display(
                start_epoch_ms=st.session_state["timer_start"].timestamp() * 1000,
                base_elapsed_ms=st.session_state["timer_elapsed_seconds"] * 1000,
                key="study_timer",
            )
        else:
            st.metric("Elapsed", format_duration(st.session_state["timer_elapsed_seconds"] / 60))

        btn_col1, btn_col2, btn_col3 = st.columns(3)
        if not st.session_state["timer_running"] and st.session_state["timer_elapsed_seconds"] == 0.0:
            btn_col1.button("▶️ Start", on_click=_start_timer, use_container_width=True)
        elif st.session_state["timer_running"]:
            btn_col1.button("⏸️ Pause", on_click=_pause_timer, use_container_width=True)
        else:
            btn_col1.button("▶️ Resume", on_click=_resume_timer, use_container_width=True)

        btn_col2.button(
            "⏹️ Stop & Save",
            on_click=_stop_and_save,
            use_container_width=True,
            disabled=(st.session_state["timer_elapsed_seconds"] == 0.0 and not st.session_state["timer_running"]),
        )

        if "last_saved_duration" in st.session_state:
            st.success(
                f"Saved a {format_duration(st.session_state['last_saved_duration'])} "
                f"session for {timer_subject}!"
            )
            del st.session_state["last_saved_duration"]

        st.caption("The duration is calculated automatically -- no manual math needed.")

# ---------------------------------------------------------------------------
# Manual Entry
# ---------------------------------------------------------------------------
with manual_tab:
    st.subheader("Log a Session Manually")
    st.caption("Use this for sessions you didn't track with the timer.")

    if not subject_names:
        st.warning("Add a subject in the **Subjects** tab first.")
    else:
        with st.form("manual_study_form"):
            m_subject = st.selectbox("Subject", subject_names, key="manual_subject")
            m_date = st.date_input("Date", value=date.today(), max_value=date.today())
            m_hours = st.number_input("Hours", min_value=0, max_value=23, value=0)
            m_minutes = st.number_input("Minutes", min_value=0, max_value=59, value=30)
            m_notes = st.text_area("Notes (optional)")
            submitted = st.form_submit_button("Save Session", use_container_width=True)

        if submitted:
            total_minutes = m_hours * 60 + m_minutes
            if total_minutes <= 0:
                st.error("Duration must be greater than 0.")
            else:
                add_study_session(
                    user_id=user_id,
                    subject_id=subject_lookup[m_subject],
                    date=m_date.isoformat(),
                    duration_minutes=total_minutes,
                    source="manual",
                    notes=m_notes,
                )
                st.success(f"Logged {format_duration(total_minutes)} of {m_subject}.")

# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------
with subjects_tab:
    st.subheader("Your Subjects")

    if not subjects:
        st.caption("No subjects yet -- add your first one below.")
    else:
        for subject in subjects:
            col_name, col_delete = st.columns([4, 1])
            col_name.write(subject["name"])

            confirm_key = f"confirm_delete_subject_{subject['id']}"
            if col_delete.button("🗑️ Remove", key=f"remove_btn_{subject['id']}", use_container_width=True):
                st.session_state[confirm_key] = True

            if st.session_state.get(confirm_key):
                session_count = get_subject_session_count(user_id, subject["id"])
                with st.container(border=True):
                    if session_count > 0:
                        st.warning(
                            f"**{subject['name']}** has **{session_count}** study session(s) "
                            f"logged. Removing it will also delete those sessions permanently."
                        )
                    else:
                        st.info(f"Remove **{subject['name']}**? It has no study sessions logged.")

                    yes_col, no_col = st.columns(2)
                    if yes_col.button("Yes, remove it", key=f"yes_{subject['id']}", use_container_width=True):
                        delete_subject(user_id, subject["id"])
                        del st.session_state[confirm_key]
                        st.success(f"Removed subject: {subject['name']}")
                        st.rerun()
                    if no_col.button("Cancel", key=f"no_{subject['id']}", use_container_width=True):
                        del st.session_state[confirm_key]
                        st.rerun()

    st.divider()

    with st.form("add_subject_form"):
        new_subject = st.text_input("New subject name")
        add_submitted = st.form_submit_button("Add Subject")

    if add_submitted:
        if not new_subject.strip():
            st.error("Subject name can't be empty.")
        else:
            add_subject(user_id, new_subject)
            st.success(f"Added subject: {new_subject.strip()}")
            st.rerun()

# ---------------------------------------------------------------------------
# Future Topics -- a "someday/maybe" study wishlist
# ---------------------------------------------------------------------------
with future_tab:
    st.subheader("What I Want to Study in the Future")
    st.caption(
        "A running list of topics/subjects you want to get to eventually -- not tied to any "
        "date or goal yet. When you're ready to actually schedule one, turn it into a Long-Term "
        "Goal on the Goals & Tasks page."
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
