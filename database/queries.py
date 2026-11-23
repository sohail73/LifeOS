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
            -- Only rewrite the row when a value really changed. Refreshing an
            -- identical snapshot on every new session must not count as a
            -- database change (it would trigger a pointless cloud backup).
            WHERE snapshots.period_start IS NOT excluded.period_start
               OR snapshots.period_end IS NOT excluded.period_end
               OR snapshots.study_hours IS NOT excluded.study_hours
               OR snapshots.problems_solved IS NOT excluded.problems_solved
               OR snapshots.current_streak IS NOT excluded.current_streak
               OR snapshots.goal_completion IS NOT excluded.goal_completion
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

def add_long_term_goal(
    user_id: int, title: str, start_date: str, end_date: str, notes: str = "", priority: int = 2
) -> int:
    """priority: 1 = High, 2 = Medium (default), 3 = Low -- every task
    created under this goal inherits it (see get_tasks_for_date), so
    setting it once here covers every day's task without re-setting
    it daily."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO long_term_goals (user_id, title, start_date, end_date, notes, priority) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title.strip(), start_date, end_date, notes.strip() if notes else None, priority),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_long_term_goals(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, start_date, end_date, notes, priority, goal_order FROM long_term_goals "
            "WHERE user_id = ? ORDER BY priority, goal_order, start_date DESC, id DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _goal_priority_tier(conn, user_id: int, goal_id: int) -> list:
    """Goals sharing this goal's priority, in their current display order."""
    rows = conn.execute(
        "SELECT id, priority FROM long_term_goals WHERE user_id = ? "
        "ORDER BY priority, goal_order, start_date DESC, id DESC",
        (user_id,),
    ).fetchall()
    rows = [dict(r) for r in rows]
    this = next((r for r in rows if r["id"] == goal_id), None)
    if this is None:
        return []
    return [r["id"] for r in rows if r["priority"] == this["priority"]]


def goal_move_availability(user_id: int, goal_id: int) -> tuple:
    """(can_move_up, can_move_down) among goals of the same priority."""
    conn = get_connection()
    try:
        tier = _goal_priority_tier(conn, user_id, goal_id)
        if goal_id not in tier:
            return False, False
        idx = tier.index(goal_id)
        return idx > 0, idx < len(tier) - 1
    finally:
        conn.close()


def move_goal_order(user_id: int, goal_id: int, direction: str) -> None:
    """
    Move a goal up or down among goals of the SAME priority (never across
    High/Medium/Low -- priority still sets the tier). Because every day's
    tasks inherit their goal's position (see get_tasks_for_date), this is
    a permanent setting: do it once here instead of per day.
    direction: 'up' or 'down'.
    """
    conn = get_connection()
    try:
        tier = _goal_priority_tier(conn, user_id, goal_id)
        if goal_id not in tier:
            return
        idx = tier.index(goal_id)
        neighbor_idx = idx - 1 if direction == "up" else idx + 1
        if neighbor_idx < 0 or neighbor_idx >= len(tier):
            return
        tier[idx], tier[neighbor_idx] = tier[neighbor_idx], tier[idx]
        # Renumber the whole tier so legacy ties (all 0) can't make the swap a no-op.
        for position, gid in enumerate(tier, start=1):
            conn.execute(
                "UPDATE long_term_goals SET goal_order = ? WHERE id = ? AND user_id = ?",
                (position, gid, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def set_goal_priority(user_id: int, goal_id: int, priority: int) -> None:
    """priority: 1 = High, 2 = Medium, 3 = Low. Every task linked to this
    goal (past, present, and future) inherits it automatically."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE long_term_goals SET priority = ? WHERE user_id = ? AND id = ?",
            (priority, user_id, goal_id),
        )
        conn.commit()
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


def goal_has_completed_tasks(user_id: int, goal_id: int) -> bool:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND goal_id = ? AND is_done = 1",
            (user_id, goal_id),
        ).fetchone()
        return row[0] > 0
    finally:
        conn.close()


def shift_goal_start_date(user_id: int, goal_id: int, new_start_date: str) -> dict:
    """
    Moves a whole goal so it starts on new_start_date instead: the goal's
    start and end dates and every one of its tasks all move by the same
    number of days, so the schedule keeps its exact shape (e.g. a goal
    planned to start 3 months from now can be pulled back to start today).

    Only allowed while the goal has no completed task yet -- once you've
    ticked tasks off, moving the whole schedule would no longer line up with
    the days you actually did them (use Extend / reschedule a task instead).
    Raises ValueError with a readable message otherwise.
    Returns {"shift_days": int, "new_end_date": "YYYY-MM-DD"}.
    """
    from datetime import date, timedelta

    conn = get_connection()
    try:
        goal = conn.execute(
            "SELECT start_date, end_date FROM long_term_goals WHERE user_id = ? AND id = ?",
            (user_id, goal_id),
        ).fetchone()
        if goal is None:
            raise ValueError("Goal not found.")
        done = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND goal_id = ? AND is_done = 1",
            (user_id, goal_id),
        ).fetchone()[0]
        if done:
            raise ValueError(
                "This goal already has completed tasks, so its start date can't be moved. "
                "Use Extend for the deadline, or reschedule individual tasks."
            )

        old_start = date.fromisoformat(goal["start_date"])
        old_end = date.fromisoformat(goal["end_date"])
        shift_days = (date.fromisoformat(new_start_date) - old_start).days
        new_end = old_end + timedelta(days=shift_days)
        if shift_days != 0:
            conn.execute(
                "UPDATE long_term_goals SET start_date = ?, end_date = ? WHERE user_id = ? AND id = ?",
                (new_start_date, new_end.isoformat(), user_id, goal_id),
            )
            conn.execute(
                "UPDATE tasks SET task_date = date(task_date, ?) WHERE user_id = ? AND goal_id = ?",
                (f"{shift_days:+d} days", user_id, goal_id),
            )
            conn.commit()
        return {"shift_days": shift_days, "new_end_date": new_end.isoformat()}
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
    priority: int = 2,
) -> int:
    """planned_start_time/planned_end_time are optional 'HH:MM' strings --
    when both are given, the completion popup pre-fills the duration
    from them instead of a flat default. priority: 1 = High, 2 = Medium
    (default), 3 = Low -- controls the order tasks show in on a given day."""
    conn = get_connection()
    try:
        next_order = conn.execute(
            "SELECT COALESCE(MAX(task_order), 0) + 1 FROM tasks WHERE user_id = ? AND task_date = ?",
            (user_id, task_date),
        ).fetchone()[0]
        cursor = conn.execute(
            "INSERT INTO tasks (user_id, goal_id, title, task_date, planned_start_time, planned_end_time, priority, task_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, goal_id, title.strip(), task_date, planned_start_time, planned_end_time, priority, next_order),
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
            "planned_start_time, planned_end_time, priority FROM tasks WHERE user_id = ? AND id = ?",
            (user_id, task_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_tasks_for_date(user_id: int, task_date: str) -> list:
    """
    A task linked to a long-term goal inherits that goal's priority
    (set once on the goal, not re-set per day) -- a standalone task
    (no goal) uses its own priority. COALESCE picks the goal's value
    when present, falling back to the task's own otherwise.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT t.id, t.title, t.is_done, t.goal_id, t.linked_session_id,
                   t.planned_start_time, t.planned_end_time,
                   COALESCE(g.priority, t.priority) AS priority, g.title AS goal_title
            FROM tasks t
            LEFT JOIN long_term_goals g ON g.id = t.goal_id
            WHERE t.user_id = ? AND t.task_date = ?
            ORDER BY priority, (t.goal_id IS NULL), g.goal_order, g.start_date DESC, g.id DESC,
                     t.task_order, t.id
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
            SELECT t.id, t.title, t.task_date, t.is_done, t.linked_session_id,
                   t.planned_start_time, t.planned_end_time,
                   COALESCE(g.priority, t.priority) AS priority
            FROM tasks t
            LEFT JOIN long_term_goals g ON g.id = t.goal_id
            WHERE t.user_id = ? AND t.goal_id = ?
            ORDER BY t.task_date, t.id
            """,
            (user_id, goal_id),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def set_task_priority(user_id: int, task_id: int, priority: int) -> None:
    """priority: 1 = High, 2 = Medium, 3 = Low."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE tasks SET priority = ? WHERE user_id = ? AND id = ?",
            (priority, user_id, task_id),
        )
        conn.commit()
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
        avatar = row["avatar_base64"] if row else None
        if avatar:
            # An old, full-size photo is sent to the browser on every page load: shrink it once and keep the small copy.
            from utils.avatar import shrink_avatar_b64

            small = shrink_avatar_b64(avatar)
            if small != avatar:
                conn.execute("UPDATE users SET avatar_base64 = ? WHERE id = ?", (small, user_id))
                conn.commit()
                avatar = small
        return avatar
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
        conn.execute("DELETE FROM leave_days WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM calendar_events WHERE user_id = ?", (user_id,))
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


# ---------------------------------------------------------------------------
# Career milestones (a roadmap of targets: internship, placement,
# hackathon, competition, job -- each with an optional target date)
# ---------------------------------------------------------------------------

def add_career_milestone(
    user_id: int,
    milestone_type: str,
    title: str,
    target_date: Optional[str] = None,
    status: str = "Upcoming",
    notes: str = "",
) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO career_milestones
                (user_id, milestone_type, title, target_date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                milestone_type,
                title.strip(),
                target_date,
                status,
                notes.strip() if notes else None,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_career_milestones(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, milestone_type, title, target_date, status, notes, created_at
            FROM career_milestones
            WHERE user_id = ?
            ORDER BY (target_date IS NULL), target_date, created_at
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_career_milestone(
    user_id: int,
    milestone_id: int,
    milestone_type: str,
    title: str,
    target_date: Optional[str],
    status: str,
    notes: str,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE career_milestones
            SET milestone_type = ?, title = ?, target_date = ?, status = ?, notes = ?
            WHERE user_id = ? AND id = ?
            """,
            (
                milestone_type,
                title.strip(),
                target_date,
                status,
                notes.strip() if notes else None,
                user_id,
                milestone_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_career_milestone(user_id: int, milestone_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM career_milestones WHERE user_id = ? AND id = ?", (user_id, milestone_id)
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Reward milestones (a personal reward ladder: "once I reach X, I'll
# do/get Y" -- trigger_value is optional, used only to sort the ladder)
# ---------------------------------------------------------------------------

def add_reward_milestone(
    user_id: int,
    milestone_label: str,
    reward_description: str,
    trigger_value: Optional[float] = None,
    notes: str = "",
) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO reward_milestones
                (user_id, milestone_label, trigger_value, reward_description, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                milestone_label.strip(),
                trigger_value,
                reward_description.strip(),
                notes.strip() if notes else None,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_reward_milestones(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, milestone_label, trigger_value, reward_description, is_achieved, notes, created_at
            FROM reward_milestones
            WHERE user_id = ?
            ORDER BY (trigger_value IS NULL), trigger_value, created_at
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_reward_milestone(
    user_id: int,
    reward_id: int,
    milestone_label: str,
    reward_description: str,
    trigger_value: Optional[float],
    notes: str,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE reward_milestones
            SET milestone_label = ?, reward_description = ?, trigger_value = ?, notes = ?
            WHERE user_id = ? AND id = ?
            """,
            (
                milestone_label.strip(),
                reward_description.strip(),
                trigger_value,
                notes.strip() if notes else None,
                user_id,
                reward_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def toggle_reward_milestone(user_id: int, reward_id: int, is_achieved: bool) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE reward_milestones SET is_achieved = ? WHERE user_id = ? AND id = ?",
            (1 if is_achieved else 0, user_id, reward_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_reward_milestone(user_id: int, reward_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM reward_milestones WHERE user_id = ? AND id = ?", (user_id, reward_id)
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Job targets (which jobs the user is aiming for: Ready / In Progress
# / Future -- In Progress can be linked to long-term goal(s), same
# auto-promote-to-Ready pattern as projects)
# ---------------------------------------------------------------------------

def add_job_target(
    user_id: int,
    title: str,
    company: str = "",
    status: str = "Future",
    notes: str = "",
    deadline: Optional[str] = None,
    target_package: str = "",
) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO job_targets (user_id, title, company, status, notes, deadline, target_package)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                title.strip(),
                company.strip() if company else None,
                status,
                notes.strip() if notes else None,
                deadline,
                target_package.strip() if target_package else None,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_job_targets(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, company, status, notes, deadline, target_package, is_pinned, created_at "
            "FROM job_targets WHERE user_id = ? ORDER BY (deadline IS NULL), deadline, created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_pinned_job_target(user_id: int) -> Optional[dict]:
    """The single job target (if any) pinned to show its countdown on the Dashboard."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, title, company, status, notes, deadline, target_package, is_pinned, created_at "
            "FROM job_targets WHERE user_id = ? AND is_pinned = 1 LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_job_target_pinned(user_id: int, job_target_id: int, pinned: bool) -> None:
    """Pin a job target's countdown to the Dashboard. Only one can be
    pinned at a time, so pinning one un-pins any other."""
    conn = get_connection()
    try:
        if pinned:
            conn.execute("UPDATE job_targets SET is_pinned = 0 WHERE user_id = ?", (user_id,))
        conn.execute(
            "UPDATE job_targets SET is_pinned = ? WHERE user_id = ? AND id = ?",
            (1 if pinned else 0, user_id, job_target_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_job_target(
    user_id: int,
    job_target_id: int,
    title: str,
    company: str,
    status: str,
    notes: str,
    deadline: Optional[str] = None,
    target_package: str = "",
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE job_targets
            SET title = ?, company = ?, status = ?, notes = ?, deadline = ?, target_package = ?
            WHERE user_id = ? AND id = ?
            """,
            (
                title.strip(),
                company.strip() if company else None,
                status,
                notes.strip() if notes else None,
                deadline,
                target_package.strip() if target_package else None,
                user_id,
                job_target_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def mark_job_target_achieved(user_id: int, job_target_id: int) -> None:
    """"Mil gayi" -- got the job before (or by) the deadline."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE job_targets SET status = 'Achieved' WHERE user_id = ? AND id = ?",
            (user_id, job_target_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_job_target(user_id: int, job_target_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM job_targets WHERE user_id = ? AND id = ?", (user_id, job_target_id))
        conn.commit()
    finally:
        conn.close()


def link_job_target_goal(user_id: int, job_target_id: int, goal_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO job_target_goals (job_target_id, goal_id) "
            "SELECT ?, ? WHERE EXISTS (SELECT 1 FROM job_targets WHERE id = ? AND user_id = ?)",
            (job_target_id, goal_id, job_target_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def unlink_job_target_goal(user_id: int, job_target_id: int, goal_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM job_target_goals WHERE job_target_id = ? AND goal_id = ? "
            "AND EXISTS (SELECT 1 FROM job_targets WHERE id = ? AND user_id = ?)",
            (job_target_id, goal_id, job_target_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_linked_goals_for_job_target(user_id: int, job_target_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT g.id, g.title, g.start_date, g.end_date, g.notes
            FROM job_target_goals jg
            JOIN long_term_goals g ON g.id = jg.goal_id
            JOIN job_targets j ON j.id = jg.job_target_id
            WHERE jg.job_target_id = ? AND j.user_id = ?
            ORDER BY g.start_date
            """,
            (job_target_id, user_id),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Career notes (a free-form scratchpad -- anything worth jotting down
# so you don't forget it: "this job needs one more goal I haven't
# created yet", reminders, loose ideas, whatever)
# ---------------------------------------------------------------------------

def add_career_note(user_id: int, content: str) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO career_notes (user_id, content) VALUES (?, ?)",
            (user_id, content.strip()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_career_notes(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, content, is_done, created_at FROM career_notes "
            "WHERE user_id = ? ORDER BY is_done, created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_career_note(user_id: int, note_id: int, content: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE career_notes SET content = ? WHERE user_id = ? AND id = ?",
            (content.strip(), user_id, note_id),
        )
        conn.commit()
    finally:
        conn.close()


def toggle_career_note(user_id: int, note_id: int, is_done: bool) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE career_notes SET is_done = ? WHERE user_id = ? AND id = ?",
            (1 if is_done else 0, user_id, note_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_career_note(user_id: int, note_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM career_notes WHERE user_id = ? AND id = ?", (user_id, note_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Roadmap steps (a sequential learning path -- Data Science, then DL,
# then MLOps, then Cloud, then AWS, then LLM, then RAG -- shown as a
# flowchart on the Career page). Same status vocabulary and
# auto-promote pattern as job_targets: Ready / In Progress / Future.
# ---------------------------------------------------------------------------

def add_roadmap_step(
    user_id: int,
    title: str,
    status: str = "Future",
    notes: str = "",
    lane: int = 1,
    order_index: Optional[int] = None,
) -> int:
    """
    Adds a step to a lane (parallel track). order_index is the step number
    within the lane: leave it None/0 to append after the lane's last step,
    or give an existing number to run in parallel with the other step(s)
    that share it (e.g. FastAPI and Cloud both numbered 4).
    """
    conn = get_connection()
    try:
        if not order_index:
            max_order = conn.execute(
                "SELECT COALESCE(MAX(order_index), 0) FROM roadmap_steps WHERE user_id = ? AND lane = ?",
                (user_id, lane),
            ).fetchone()[0]
            order_index = max_order + 1
        cursor = conn.execute(
            "INSERT INTO roadmap_steps (user_id, title, order_index, status, notes, lane) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title.strip(), order_index, status, notes.strip() if notes else None, lane),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_roadmap_steps(user_id: int) -> list:
    """All steps, grouped by lane (track) then in order within the lane."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, order_index, status, notes, lane, created_at FROM roadmap_steps "
            "WHERE user_id = ? ORDER BY lane, order_index, id",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_roadmap_step(
    user_id: int,
    step_id: int,
    title: str,
    status: str,
    notes: str,
    lane: Optional[int] = None,
    order_index: Optional[int] = None,
) -> None:
    """
    lane=None keeps the current lane; a different lane moves the step to
    the end of that lane (unless order_index is also given). order_index
    is the step number inside the lane -- steps sharing a number run in
    parallel; None leaves it unchanged.
    """
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE roadmap_steps SET title = ?, status = ?, notes = ? WHERE user_id = ? AND id = ?",
            (title.strip(), status, notes.strip() if notes else None, user_id, step_id),
        )
        if lane is not None:
            current = conn.execute(
                "SELECT lane FROM roadmap_steps WHERE user_id = ? AND id = ?", (user_id, step_id)
            ).fetchone()
            if current is not None and current["lane"] != lane:
                max_order = conn.execute(
                    "SELECT COALESCE(MAX(order_index), 0) FROM roadmap_steps WHERE user_id = ? AND lane = ?",
                    (user_id, lane),
                ).fetchone()[0]
                conn.execute(
                    "UPDATE roadmap_steps SET lane = ?, order_index = ? WHERE user_id = ? AND id = ?",
                    (lane, max_order + 1, user_id, step_id),
                )
        if order_index:
            conn.execute(
                "UPDATE roadmap_steps SET order_index = ? WHERE user_id = ? AND id = ?",
                (order_index, user_id, step_id),
            )
        conn.commit()
    finally:
        conn.close()


def delete_roadmap_step(user_id: int, step_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM roadmap_steps WHERE user_id = ? AND id = ?", (user_id, step_id))
        conn.commit()
    finally:
        conn.close()


def move_roadmap_step(user_id: int, step_id: int, direction: str) -> None:
    """
    direction: 'up' or 'down'. Moves this step's whole stage (every step
    sharing its step number in the lane) one stage earlier/later by
    swapping step numbers with the adjacent stage -- so steps that run in
    parallel stay together.
    """
    conn = get_connection()
    try:
        this = conn.execute(
            "SELECT lane, order_index FROM roadmap_steps WHERE user_id = ? AND id = ?", (user_id, step_id)
        ).fetchone()
        if this is None:
            return
        stages = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT order_index FROM roadmap_steps WHERE user_id = ? AND lane = ? ORDER BY order_index",
                (user_id, this["lane"]),
            ).fetchall()
        ]
        idx = stages.index(this["order_index"])
        neighbor_idx = idx - 1 if direction == "up" else idx + 1
        if neighbor_idx < 0 or neighbor_idx >= len(stages):
            return
        a, b = stages[idx], stages[neighbor_idx]
        where = "user_id = ? AND lane = ? AND order_index = ?"
        conn.execute(f"UPDATE roadmap_steps SET order_index = -1 WHERE {where}", (user_id, this["lane"], a))
        conn.execute(f"UPDATE roadmap_steps SET order_index = ? WHERE {where}", (a, user_id, this["lane"], b))
        conn.execute(f"UPDATE roadmap_steps SET order_index = ? WHERE {where}", (b, user_id, this["lane"], -1))
        conn.commit()
    finally:
        conn.close()


def link_roadmap_step_goal(user_id: int, step_id: int, goal_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO roadmap_step_goals (step_id, goal_id) "
            "SELECT ?, ? WHERE EXISTS (SELECT 1 FROM roadmap_steps WHERE id = ? AND user_id = ?)",
            (step_id, goal_id, step_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def unlink_roadmap_step_goal(user_id: int, step_id: int, goal_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM roadmap_step_goals WHERE step_id = ? AND goal_id = ? "
            "AND EXISTS (SELECT 1 FROM roadmap_steps WHERE id = ? AND user_id = ?)",
            (step_id, goal_id, step_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_linked_goals_for_roadmap_step(user_id: int, step_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT g.id, g.title, g.start_date, g.end_date, g.notes
            FROM roadmap_step_goals sg
            JOIN long_term_goals g ON g.id = sg.goal_id
            JOIN roadmap_steps s ON s.id = sg.step_id
            WHERE sg.step_id = ? AND s.user_id = ?
            ORDER BY g.start_date
            """,
            (step_id, user_id),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Gym sessions (workout log: date, type, duration, notes)
# ---------------------------------------------------------------------------

def add_gym_session(
    user_id: int,
    date: str,
    workout_type: str,
    duration_minutes: Optional[float] = None,
    notes: str = "",
) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO gym_sessions (user_id, date, workout_type, duration_minutes, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, date, workout_type, duration_minutes, notes.strip() if notes else None),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_gym_sessions_df(user_id: int) -> pd.DataFrame:
    conn = get_connection()
    try:
        query = (
            "SELECT id, date, workout_type, duration_minutes, notes FROM gym_sessions "
            "WHERE user_id = ? ORDER BY date"
        )
        df = pd.read_sql_query(query, conn, params=(user_id,))
    finally:
        conn.close()

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def get_gym_sessions(user_id: int) -> list:
    """Most-recent-first list of gym sessions, for display/deletion in the UI."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, date, workout_type, duration_minutes, notes FROM gym_sessions "
            "WHERE user_id = ? ORDER BY date DESC, id DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_gym_session(user_id: int, session_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM gym_sessions WHERE user_id = ? AND id = ?", (user_id, session_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Leave days (streak freeze: days you were away -- never break a streak,
# shown in blue on the streak heatmaps)
# ---------------------------------------------------------------------------

def add_leave_days(user_id: int, start_date: str, end_date: str, reason: str = "") -> int:
    """Mark every day from start_date to end_date (inclusive, ISO strings)
    as leave. Days already marked are left alone. Returns how many new
    days were added."""
    from datetime import date as _date, timedelta as _td

    start = _date.fromisoformat(start_date)
    end = _date.fromisoformat(end_date)
    if end < start:
        start, end = end, start

    added = 0
    conn = get_connection()
    try:
        day = start
        while day <= end:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO leave_days (user_id, leave_date, reason) VALUES (?, ?, ?)",
                (user_id, day.isoformat(), reason.strip() if reason else None),
            )
            added += cursor.rowcount
            day += _td(days=1)
        conn.commit()
        return added
    finally:
        conn.close()


def get_leave_days(user_id: int) -> list:
    """Most-recent-first list of leave days, for display/removal in the UI."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, leave_date, reason FROM leave_days WHERE user_id = ? ORDER BY leave_date DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_leave_dates(user_id: int) -> set:
    """Set of datetime.date objects the user marked as leave."""
    from datetime import date as _date

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT leave_date FROM leave_days WHERE user_id = ?", (user_id,)
        ).fetchall()
        return {_date.fromisoformat(r["leave_date"]) for r in rows}
    finally:
        conn.close()


def delete_leave_day(user_id: int, leave_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM leave_days WHERE user_id = ? AND id = ?", (user_id, leave_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Calendar events (internships, interviews, exams, deadlines... on the
# Calendar page)
# ---------------------------------------------------------------------------

def add_calendar_event(
    user_id: int,
    title: str,
    category: str,
    start_date: str,
    end_date: str,
    company: str = "",
    notes: str = "",
) -> int:
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO calendar_events (user_id, title, category, company, start_date, end_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, title.strip(), category, company.strip() or None,
                start_date, end_date, notes.strip() or None,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_calendar_events(user_id: int) -> list:
    """All of a user's calendar events, soonest start first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, category, company, start_date, end_date, notes "
            "FROM calendar_events WHERE user_id = ? ORDER BY start_date, id",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_calendar_event(
    user_id: int,
    event_id: int,
    title: str,
    category: str,
    start_date: str,
    end_date: str,
    company: str = "",
    notes: str = "",
) -> None:
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE calendar_events
            SET title = ?, category = ?, company = ?, start_date = ?, end_date = ?, notes = ?
            WHERE user_id = ? AND id = ?
            """,
            (
                title.strip(), category, company.strip() or None, start_date, end_date,
                notes.strip() or None, user_id, event_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_calendar_event(user_id: int, event_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM calendar_events WHERE user_id = ? AND id = ?", (user_id, event_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Job roles (a role you're building toward, ready once its attached roadmap
# steps are all Ready -- see analytics/goal_maintenance.job_role_readiness)
# ---------------------------------------------------------------------------

def add_job_role(user_id: int, title: str, notes: str = "") -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO job_roles (user_id, title, notes) VALUES (?, ?, ?)",
            (user_id, title.strip(), notes.strip() if notes else None),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_job_roles(user_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, notes, created_at FROM job_roles WHERE user_id = ? ORDER BY created_at, id",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_job_role(user_id: int, role_id: int, title: str, notes: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE job_roles SET title = ?, notes = ? WHERE user_id = ? AND id = ?",
            (title.strip(), notes.strip() if notes else None, user_id, role_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_job_role(user_id: int, role_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM job_roles WHERE user_id = ? AND id = ?", (user_id, role_id))
        conn.commit()
    finally:
        conn.close()


def set_job_role_steps(user_id: int, role_id: int, step_ids: list) -> None:
    """Replace the set of roadmap steps attached to a role. Only steps and roles
    that belong to this user are accepted; anything else is silently ignored."""
    conn = get_connection()
    try:
        owns_role = conn.execute(
            "SELECT 1 FROM job_roles WHERE id = ? AND user_id = ?", (role_id, user_id)
        ).fetchone()
        if owns_role is None:
            return
        conn.execute("DELETE FROM job_role_steps WHERE role_id = ?", (role_id,))
        for step_id in dict.fromkeys(step_ids):  # de-duplicate, keep order
            conn.execute(
                "INSERT OR IGNORE INTO job_role_steps (role_id, step_id) "
                "SELECT ?, id FROM roadmap_steps WHERE id = ? AND user_id = ?",
                (role_id, step_id, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_job_role_steps(user_id: int, role_id: int) -> list:
    """The roadmap steps attached to a role, in roadmap order (track, then step number)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.status, s.lane, s.order_index
            FROM job_role_steps jr
            JOIN roadmap_steps s ON s.id = jr.step_id
            JOIN job_roles r ON r.id = jr.role_id
            WHERE jr.role_id = ? AND r.user_id = ?
            ORDER BY s.lane, s.order_index, s.id
            """,
            (role_id, user_id),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

