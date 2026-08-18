"""
database/queries.py

All parameterized SQLite read/write queries used by the app, in one
place. Pages and analytics code should call these functions instead
of writing raw SQL themselves -- keeps the DB layer swappable later
and guarantees every query is parameterized (never string-built from
user input).

Every function takes user_id explicitly and filters on it, so one
user's data can never leak into another user's queries.
"""

from datetime import datetime
from typing import Optional

import pandas as pd

from config.database import get_connection
from config.constants import CODING_LANGUAGES_DEFAULT, DEFAULT_SUBJECTS


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------

def ensure_default_subjects(user_id: int) -> None:
    """Seed a new user's subject list with sensible defaults (idempotent)."""
    conn = get_connection()
    try:
        for name in DEFAULT_SUBJECTS:
            conn.execute(
                "INSERT OR IGNORE INTO subjects (user_id, name) VALUES (?, ?)",
                (user_id, name),
            )
        conn.commit()
    finally:
        conn.close()


def get_subjects(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, name FROM subjects WHERE user_id = ? ORDER BY name",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_subject(user_id: int, name: str) -> Optional[int]:
    name = name.strip()
    if not name:
        return None
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO subjects (user_id, name) VALUES (?, ?)",
            (user_id, name),
        )
        conn.commit()
        if cursor.rowcount == 0:
            # Already exists -- return its id anyway.
            row = conn.execute(
                "SELECT id FROM subjects WHERE user_id = ? AND name = ?",
                (user_id, name),
            ).fetchone()
            return row["id"] if row else None
        return cursor.lastrowid
    finally:
        conn.close()


def get_subject_session_count(user_id: int, subject_id: int) -> int:
    """How many study sessions are logged under this subject (for a delete warning)."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM study_sessions WHERE user_id = ? AND subject_id = ?",
            (user_id, subject_id),
        ).fetchone()
        return int(row["n"]) if row else 0
    finally:
        conn.close()


def delete_subject(user_id: int, subject_id: int) -> None:
    """
    Delete a subject. Because study_sessions has ON DELETE CASCADE on
    subject_id, any sessions logged under it are removed too -- the
    UI should warn about that count (get_subject_session_count) before
    calling this.
    """
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM subjects WHERE user_id = ? AND id = ?", (user_id, subject_id)
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Study sessions
# ---------------------------------------------------------------------------

def add_study_session(
    user_id: int,
    subject_id: int,
    date: str,
    duration_minutes: float,
    source: str = "manual",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    notes: str = "",
) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO study_sessions
                (user_id, subject_id, date, duration_minutes, start_time, end_time, source, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                subject_id,
                date,
                duration_minutes,
                start_time,
                end_time,
                source,
                notes.strip() if notes else None,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_study_sessions_df(user_id: int) -> pd.DataFrame:
    """All study sessions for a user, joined with subject name, as a DataFrame."""
    conn = get_connection()
    try:
        query = """
            SELECT
                ss.id,
                ss.date,
                ss.duration_minutes,
                ss.source,
                ss.notes,
                s.name AS subject
            FROM study_sessions ss
            JOIN subjects s ON s.id = ss.subject_id
            WHERE ss.user_id = ?
            ORDER BY ss.date
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
    finally:
        conn.close()

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


# ---------------------------------------------------------------------------
# Coding logs
# ---------------------------------------------------------------------------

def add_coding_log(
    user_id: int,
    platform: str,
    problem_name: str,
    language: str,
    difficulty: str,
    topic: str,
    date_solved: str,
    time_taken_minutes: Optional[float] = None,
    notes: str = "",
    source: str = "manual",
    external_id: Optional[str] = None,
) -> Optional[int]:
    """
    Insert a coding log. `source`/`external_id` are used by the
    LeetCode sync (source='leetcode', external_id=problem slug) so a
    re-sync can tell which problems are already logged instead of
    creating duplicates -- see get_synced_external_ids. Manual entries
    leave both at their defaults. Returns None if this external_id was
    already logged for this user (duplicate sync, silently skipped).
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO coding_logs
                (user_id, platform, problem_name, language, difficulty, topic,
                 date_solved, time_taken_minutes, notes, source, external_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                platform,
                problem_name.strip(),
                language,
                difficulty,
                topic,
                date_solved,
                time_taken_minutes,
                notes.strip() if notes else None,
                source,
                external_id,
            ),
        )
        conn.commit()
        return cursor.lastrowid if cursor.rowcount else None
    finally:
        conn.close()


def get_synced_external_ids(user_id: int) -> set:
    """External IDs (LeetCode problem slugs) already logged for this user, for dedupe."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT external_id FROM coding_logs WHERE user_id = ? AND external_id IS NOT NULL",
            (user_id,),
        ).fetchall()
        return {r["external_id"] for r in rows}
    finally:
        conn.close()


def get_coding_logs_df(user_id: int) -> pd.DataFrame:
    conn = get_connection()
    try:
        query = """
            SELECT id, platform, problem_name, language, difficulty, topic,
                   date_solved, time_taken_minutes, notes, source
            FROM coding_logs
            WHERE user_id = ?
            ORDER BY date_solved
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
    finally:
        conn.close()

    if not df.empty:
        df["date_solved"] = pd.to_datetime(df["date_solved"])
    return df




# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------

def get_goals(user_id: int) -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT daily_study_minutes_goal, daily_problems_goal "
            "FROM goals WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            # Safety net -- should normally be created at signup.
            conn.execute("INSERT INTO goals (user_id) VALUES (?)", (user_id,))
            conn.commit()
            return {"daily_study_minutes_goal": 60, "daily_problems_goal": 2}
        return dict(row)
    finally:
        conn.close()


def update_goals(user_id: int, daily_study_minutes_goal: int, daily_problems_goal: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE goals
            SET daily_study_minutes_goal = ?,
                daily_problems_goal = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (daily_study_minutes_goal, daily_problems_goal, datetime.now().isoformat(), user_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

def save_snapshot(
    user_id: int,
    snapshot_type: str,
    period_label: str,
    period_start: str,
    period_end: str,
    study_hours: float,
    problems_solved: int,
    current_streak: int,
    goal_completion: float,
) -> None:
    """Insert or overwrite the snapshot for this user/type/period."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO snapshots
                (user_id, snapshot_type, period_label, period_start, period_end,
                 study_hours, problems_solved, current_streak, goal_completion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id, snapshot_type, period_label)
            DO UPDATE SET
                period_start = excluded.period_start,
                period_end = excluded.period_end,
                study_hours = excluded.study_hours,
                problems_solved = excluded.problems_solved,
                current_streak = excluded.current_streak,
                goal_completion = excluded.goal_completion,
                created_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                snapshot_type,
                period_label,
                period_start,
                period_end,
                study_hours,
                problems_solved,
                current_streak,
                goal_completion,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_snapshots_df(user_id: int, snapshot_type: Optional[str] = None) -> pd.DataFrame:
    conn = get_connection()
    try:
        if snapshot_type:
            query = (
                "SELECT * FROM snapshots WHERE user_id = ? AND snapshot_type = ? "
                "ORDER BY period_start"
            )
            df = pd.read_sql_query(query, conn, params=(user_id, snapshot_type))
        else:
            query = "SELECT * FROM snapshots WHERE user_id = ? ORDER BY period_start"
            df = pd.read_sql_query(query, conn, params=(user_id,))
    finally:
        conn.close()
    return df


# ---------------------------------------------------------------------------
# Long-term goals (e.g. "Crack the job in 60 days", "Finish DSA in 3 months")
# ---------------------------------------------------------------------------

def add_long_term_goal(user_id: int, title: str, start_date: str, end_date: str, notes: str = "") -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO long_term_goals (user_id, title, start_date, end_date, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, title.strip(), start_date, end_date, notes.strip() if notes else None),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_long_term_goals(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, start_date, end_date, notes FROM long_term_goals "
            "WHERE user_id = ? ORDER BY start_date DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def extend_goal_end_date(user_id: int, goal_id: int, new_end_date: str) -> None:
    """
    Sets a goal's deadline to new_end_date -- used both to push it out
    (fell behind schedule) and to pull it in (finished a task early,
    see pull_task_forward in analytics/goal_maintenance.py). The name
    reflects the common case; it's a plain UPDATE either direction.
    """
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE long_term_goals SET end_date = ? WHERE user_id = ? AND id = ?",
            (new_end_date, user_id, goal_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_goal_notes(user_id: int, goal_id: int, notes: str) -> None:
    """Add or edit a goal's description/notes after it's already been created."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE long_term_goals SET notes = ? WHERE user_id = ? AND id = ?",
            (notes.strip() if notes and notes.strip() else None, user_id, goal_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_long_term_goal(user_id: int, goal_id: int) -> None:
    """
    Deletes the goal AND every task linked to it (past or future) --
    a deleted goal shouldn't leave its planned tasks still showing up
    in Today's Tasks. Any study time already logged from completed
    tasks stays intact (study_sessions rows aren't touched), so
    Analytics/Dashboard history is unaffected -- only the checklist
    entries themselves go away.
    """
    conn = get_connection()
    try:
        conn.execute("DELETE FROM tasks WHERE user_id = ? AND goal_id = ?", (user_id, goal_id))
        conn.execute(
            "DELETE FROM long_term_goals WHERE user_id = ? AND id = ?", (user_id, goal_id)
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Daily tasks
# ---------------------------------------------------------------------------

def add_task(
    user_id: int,
    title: str,
    task_date: str,
    goal_id: Optional[int] = None,
    planned_start_time: Optional[str] = None,
    planned_end_time: Optional[str] = None,
) -> int:
    """planned_start_time/planned_end_time are optional 'HH:MM' strings --
    when both are given, the completion popup pre-fills the duration
    from them instead of a flat default."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO tasks (user_id, goal_id, title, task_date, planned_start_time, planned_end_time) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, goal_id, title.strip(), task_date, planned_start_time, planned_end_time),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_task(user_id: int, task_id: int) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, title, task_date, is_done, goal_id, linked_session_id, "
            "planned_start_time, planned_end_time FROM tasks WHERE user_id = ? AND id = ?",
            (user_id, task_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_tasks_for_date(user_id: int, task_date: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT t.id, t.title, t.is_done, t.goal_id, t.linked_session_id,
                   t.planned_start_time, t.planned_end_time, g.title AS goal_title
            FROM tasks t
            LEFT JOIN long_term_goals g ON g.id = t.goal_id
            WHERE t.user_id = ? AND t.task_date = ?
            ORDER BY t.id
            """,
            (user_id, task_date),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_tasks_for_goal(user_id: int, goal_id: int) -> list:
    """All tasks (any date, done or not) belonging to one goal, oldest first --
    used by the goal detail card (Dashboard + Goals & Tasks) to list every
    topic/day so it can be checked off, rescheduled, or added to."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, title, task_date, is_done, linked_session_id,
                   planned_start_time, planned_end_time
            FROM tasks
            WHERE user_id = ? AND goal_id = ?
            ORDER BY task_date, id
            """,
            (user_id, goal_id),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_tasks_df(user_id: int, goal_id: Optional[int] = None) -> pd.DataFrame:
    """All tasks for a user (optionally filtered to one goal) as a DataFrame."""
    conn = get_connection()
    try:
        if goal_id is not None:
            query = (
                "SELECT id, title, task_date, is_done, goal_id FROM tasks "
                "WHERE user_id = ? AND goal_id = ? ORDER BY task_date"
            )
            df = pd.read_sql_query(query, conn, params=(user_id, goal_id))
        else:
            query = (
                "SELECT id, title, task_date, is_done, goal_id FROM tasks "
                "WHERE user_id = ? ORDER BY task_date"
            )
            df = pd.read_sql_query(query, conn, params=(user_id,))
    finally:
        conn.close()

    if not df.empty:
        df["task_date"] = pd.to_datetime(df["task_date"])
        df["is_done"] = df["is_done"].astype(bool)
    return df


def reschedule_task(user_id: int, task_id: int, new_date: str) -> None:
    """Move a task to a different date (e.g. it slipped and needs to move to tomorrow)."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE tasks SET task_date = ? WHERE user_id = ? AND id = ?",
            (new_date, user_id, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def complete_task_with_session(
    user_id: int,
    task_id: int,
    subject_id: int,
    duration_minutes: float,
    task_date: str,
    notes: str = "",
) -> None:
    """
    Marks a task done AND logs the actual study time behind it as a
    real study_sessions row (source='task'), so Analytics/Dashboard/
    Wrapped reflect time spent on tasks, not just a checkbox. The new
    session's id is stored on the task so un-completing it later can
    remove that session again (see uncomplete_task).
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO study_sessions (user_id, subject_id, date, duration_minutes, source, notes)
            VALUES (?, ?, ?, ?, 'task', ?)
            """,
            (user_id, subject_id, task_date, duration_minutes, notes.strip() if notes else None),
        )
        session_id = cursor.lastrowid
        conn.execute(
            "UPDATE tasks SET is_done = 1, linked_session_id = ? WHERE user_id = ? AND id = ?",
            (session_id, user_id, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def uncomplete_task(user_id: int, task_id: int) -> None:
    """
    Marks a task not-done. If it had an auto-logged study session
    (from complete_task_with_session), that session is removed too so
    the numbers stay consistent with the checkbox.
    """
    task = get_task(user_id, task_id)
    conn = get_connection()
    try:
        if task and task.get("linked_session_id"):
            conn.execute(
                "DELETE FROM study_sessions WHERE user_id = ? AND id = ?",
                (user_id, task["linked_session_id"]),
            )
        conn.execute(
            "UPDATE tasks SET is_done = 0, linked_session_id = NULL WHERE user_id = ? AND id = ?",
            (user_id, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def toggle_task(user_id: int, task_id: int, is_done: bool) -> None:
    """Simple toggle with no linked study session (used for tasks that were
    never completed with the duration/subject popup, e.g. bulk-created ones
    left unchecked)."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE tasks SET is_done = ? WHERE user_id = ? AND id = ?",
            (1 if is_done else 0, user_id, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_task(user_id: int, task_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM tasks WHERE user_id = ? AND id = ?", (user_id, task_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# User profile: LeetCode username + optional avatar
# ---------------------------------------------------------------------------

def get_leetcode_username(user_id: int) -> Optional[str]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT leetcode_username FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return row["leetcode_username"] if row else None
    finally:
        conn.close()


def set_leetcode_username(user_id: int, username: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET leetcode_username = ? WHERE id = ?",
            (username.strip() or None, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_avatar_base64(user_id: int) -> Optional[str]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT avatar_base64 FROM users WHERE id = ?", (user_id,)).fetchone()
        return row["avatar_base64"] if row else None
    finally:
        conn.close()


def set_avatar_base64(user_id: int, avatar_base64: Optional[str]) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET avatar_base64 = ? WHERE id = ?", (avatar_base64, user_id))
        conn.commit()
    finally:
        conn.close()


def get_custom_quote(user_id: int) -> Optional[str]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT custom_quote FROM users WHERE id = ?", (user_id,)).fetchone()
        return row["custom_quote"] if row else None
    finally:
        conn.close()


def set_custom_quote(user_id: int, quote: Optional[str]) -> None:
    """Pass None or an empty string to clear it and go back to the automatic daily quote."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET custom_quote = ? WHERE id = ?",
            (quote.strip() if quote and quote.strip() else None, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_password_hash(user_id: int, new_password_hash: str) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Full account data reset (Settings page, password-protected)
# ---------------------------------------------------------------------------

def reset_user_data(user_id: int) -> None:
    """
    Wipes all of a user's activity data and puts their account back to
    a fresh, just-signed-up state: no study sessions, coding logs,
    tasks, goals, or snapshots, default subjects re-seeded, and daily
    goals reset to defaults. The account itself (name/email/password)
    is untouched -- this is a data reset, not account deletion.
    """
    conn = get_connection()
    try:
        conn.execute("DELETE FROM study_sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM coding_logs WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM long_term_goals WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM snapshots WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM subjects WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM languages WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM projects WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM future_topics WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM known_skills WHERE user_id = ?", (user_id,))
        conn.execute(
            "UPDATE goals SET daily_study_minutes_goal = 60, daily_problems_goal = 2, "
            "updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,),
        )
        conn.execute(
            "UPDATE users SET leetcode_username = NULL, avatar_base64 = NULL, "
            "custom_quote = NULL WHERE id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()

    # Re-seed default subjects and languages, same as a brand-new signup.
    ensure_default_subjects(user_id)
    ensure_default_languages(user_id)


# ---------------------------------------------------------------------------
# Coding languages (user-managed, same pattern as subjects)
# ---------------------------------------------------------------------------

def ensure_default_languages(user_id: int) -> None:
    """Seed a new user's language list with sensible defaults (idempotent)."""
    conn = get_connection()
    try:
        for name in CODING_LANGUAGES_DEFAULT:
            conn.execute(
                "INSERT OR IGNORE INTO languages (user_id, name) VALUES (?, ?)",
                (user_id, name),
            )
        conn.commit()
    finally:
        conn.close()


def get_languages(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, name FROM languages WHERE user_id = ? ORDER BY name",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_language(user_id: int, name: str) -> Optional[int]:
    name = name.strip()
    if not name:
        return None
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO languages (user_id, name) VALUES (?, ?)",
            (user_id, name),
        )
        conn.commit()
        if cursor.rowcount == 0:
            row = conn.execute(
                "SELECT id FROM languages WHERE user_id = ? AND name = ?", (user_id, name)
            ).fetchone()
            return row["id"] if row else None
        return cursor.lastrowid
    finally:
        conn.close()


def delete_language(user_id: int, language_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM languages WHERE user_id = ? AND id = ?", (user_id, language_id)
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Projects (future/planned projects the user wants to track)
# ---------------------------------------------------------------------------

def add_project(
    user_id: int,
    title: str,
    description: str = "",
    status: str = "Planned",
    tech_stack: str = "",
    target_date: Optional[str] = None,
    notes: str = "",
    linked_goal_id: Optional[int] = None,
) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO projects
                (user_id, title, description, status, tech_stack, target_date, notes, linked_goal_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                title.strip(),
                description.strip() if description else None,
                status,
                tech_stack.strip() if tech_stack else None,
                target_date,
                notes.strip() if notes else None,
                linked_goal_id,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_projects(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT p.id, p.title, p.description, p.status, p.tech_stack, p.target_date,
                   p.notes, p.created_at, p.linked_goal_id, g.title AS linked_goal_title
            FROM projects p
            LEFT JOIN long_term_goals g ON g.id = p.linked_goal_id
            WHERE p.user_id = ?
            ORDER BY p.created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_project(
    user_id: int,
    project_id: int,
    title: str,
    description: str,
    status: str,
    tech_stack: str,
    target_date: Optional[str],
    notes: str,
    linked_goal_id: Optional[int] = None,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE projects
            SET title = ?, description = ?, status = ?, tech_stack = ?, target_date = ?,
                notes = ?, linked_goal_id = ?
            WHERE user_id = ? AND id = ?
            """,
            (
                title.strip(),
                description.strip() if description else None,
                status,
                tech_stack.strip() if tech_stack else None,
                target_date,
                notes.strip() if notes else None,
                linked_goal_id,
                user_id,
                project_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_project(user_id: int, project_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM projects WHERE user_id = ? AND id = ?", (user_id, project_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Future topics (a "someday/maybe" study wishlist -- not tied to a date/goal)
# ---------------------------------------------------------------------------

def add_future_topic(user_id: int, title: str, notes: str = "") -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO future_topics (user_id, title, notes) VALUES (?, ?, ?)",
            (user_id, title.strip(), notes.strip() if notes else None),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_future_topics(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, notes, created_at FROM future_topics "
            "WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_future_topic(user_id: int, topic_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM future_topics WHERE user_id = ? AND id = ?", (user_id, topic_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Known skills (a flat "what I already know" list)
# ---------------------------------------------------------------------------

def add_known_skill(user_id: int, name: str) -> Optional[int]:
    name = name.strip()
    if not name:
        return None
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO known_skills (user_id, name) VALUES (?, ?)", (user_id, name)
        )
        conn.commit()
        if cursor.rowcount == 0:
            row = conn.execute(
                "SELECT id FROM known_skills WHERE user_id = ? AND name = ?", (user_id, name)
            ).fetchone()
            return row["id"] if row else None
        return cursor.lastrowid
    finally:
        conn.close()


def get_known_skills(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, name, created_at FROM known_skills WHERE user_id = ? ORDER BY name",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_known_skill(user_id: int, skill_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM known_skills WHERE user_id = ? AND id = ?", (user_id, skill_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Project <-> Goal links (many-to-many: a project can be tracked by
# several long-term goals; see analytics.goal_maintenance for the
# auto-promote-to-Ready logic that uses this)
# ---------------------------------------------------------------------------

def link_project_goal(user_id: int, project_id: int, goal_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO project_goals (project_id, goal_id) "
            "SELECT ?, ? WHERE EXISTS (SELECT 1 FROM projects WHERE id = ? AND user_id = ?)",
            (project_id, goal_id, project_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def unlink_project_goal(user_id: int, project_id: int, goal_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM project_goals WHERE project_id = ? AND goal_id = ? "
            "AND EXISTS (SELECT 1 FROM projects WHERE id = ? AND user_id = ?)",
            (project_id, goal_id, project_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_linked_goals_for_project(user_id: int, project_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT g.id, g.title, g.start_date, g.end_date, g.notes
            FROM project_goals pg
            JOIN long_term_goals g ON g.id = pg.goal_id
            JOIN projects p ON p.id = pg.project_id
            WHERE pg.project_id = ? AND p.user_id = ?
            ORDER BY g.start_date
            """,
            (project_id, user_id),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Project <-> Future Topic links (many-to-many: a "Planned" project can
# reference one or more items from the Future Topics wishlist)
# ---------------------------------------------------------------------------

def link_project_future_topic(user_id: int, project_id: int, future_topic_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO project_future_topics (project_id, future_topic_id) "
            "SELECT ?, ? WHERE EXISTS (SELECT 1 FROM projects WHERE id = ? AND user_id = ?)",
            (project_id, future_topic_id, project_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def unlink_project_future_topic(user_id: int, project_id: int, future_topic_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM project_future_topics WHERE project_id = ? AND future_topic_id = ? "
            "AND EXISTS (SELECT 1 FROM projects WHERE id = ? AND user_id = ?)",
            (project_id, future_topic_id, project_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_linked_future_topics_for_project(user_id: int, project_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT t.id, t.title, t.notes
            FROM project_future_topics pft
            JOIN future_topics t ON t.id = pft.future_topic_id
            JOIN projects p ON p.id = pft.project_id
            WHERE pft.project_id = ? AND p.user_id = ?
            ORDER BY t.title
            """,
            (project_id, user_id),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
