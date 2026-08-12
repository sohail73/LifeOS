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
from config.constants import DEFAULT_SUBJECTS


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
) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO coding_logs
                (user_id, platform, problem_name, language, difficulty, topic,
                 date_solved, time_taken_minutes, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_coding_logs_df(user_id: int) -> pd.DataFrame:
    conn = get_connection()
    try:
        query = """
            SELECT id, platform, problem_name, language, difficulty, topic,
                   date_solved, time_taken_minutes, notes
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


def delete_long_term_goal(user_id: int, goal_id: int) -> None:
    """Deletes the goal; linked tasks are kept but unlinked (ON DELETE SET NULL)."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM long_term_goals WHERE user_id = ? AND id = ?", (user_id, goal_id)
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Daily tasks
# ---------------------------------------------------------------------------

def add_task(user_id: int, title: str, task_date: str, goal_id: Optional[int] = None) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO tasks (user_id, goal_id, title, task_date) VALUES (?, ?, ?, ?)",
            (user_id, goal_id, title.strip(), task_date),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_tasks_for_date(user_id: int, task_date: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT t.id, t.title, t.is_done, t.goal_id, g.title AS goal_title
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


def toggle_task(user_id: int, task_id: int, is_done: bool) -> None:
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
        conn.execute(
            "UPDATE goals SET daily_study_minutes_goal = 60, daily_problems_goal = 2, "
            "updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()

    # Re-seed default subjects, same as a brand-new signup.
    ensure_default_subjects(user_id)
