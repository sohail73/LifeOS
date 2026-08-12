"""
database/create_tables.py

Creates all LifeOS v0.1 tables if they don't already exist.

Scope (per the v0.1 roadmap): auth + dashboard + Study module
(subjects, study sessions, timer, goals) + coding tracker +
analytics + AI insights + snapshots + wrapped. Analytics, insights,
and wrapped are all computed on top of these tables -- they don't
need tables of their own except `snapshots`, which stores frozen
historical results.

Future modules (Finance, Health, Job Prep, ...) and the dynamic
module/widget-configuration tables are intentionally NOT created
yet -- only Study is implemented in v0.1.
"""

from config.database import get_connection


def create_users_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def create_subjects_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (user_id, name)
        )
        """
    )


def create_study_sessions_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            duration_minutes REAL NOT NULL,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            source TEXT NOT NULL DEFAULT 'manual',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_study_sessions_user_date "
        "ON study_sessions (user_id, date)"
    )


def create_coding_logs_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS coding_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            problem_name TEXT NOT NULL,
            language TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            topic TEXT NOT NULL,
            date_solved TEXT NOT NULL,
            time_taken_minutes REAL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_coding_logs_user_date "
        "ON coding_logs (user_id, date_solved)"
    )


def create_goals_table(conn) -> None:
    # One row per user holding their current daily goals. Kept simple
    # (no history) for v0.1 -- goal *completion over time* is derived
    # from study_sessions/coding_logs vs. this current target.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            daily_study_minutes_goal INTEGER NOT NULL DEFAULT 60,
            daily_problems_goal INTEGER NOT NULL DEFAULT 2,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )


def create_snapshots_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            snapshot_type TEXT NOT NULL,
            period_label TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            study_hours REAL NOT NULL DEFAULT 0,
            problems_solved INTEGER NOT NULL DEFAULT 0,
            current_streak INTEGER NOT NULL DEFAULT 0,
            goal_completion REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (user_id, snapshot_type, period_label)
        )
        """
    )


def create_long_term_goals_table(conn) -> None:
    # A milestone the user is working toward over weeks/months, e.g.
    # "Crack the job in 60 days" or "Finish DSA in 3 months". Daily
    # tasks can optionally be linked to one via tasks.goal_id.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS long_term_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )


def create_tasks_table(conn) -> None:
    # A daily to-do item, e.g. "Study DBMS today". Optionally tied to
    # a long_term_goals row so a multi-week plan can be broken into
    # day-by-day items and tracked with a streak/heatmap.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            goal_id INTEGER,
            title TEXT NOT NULL,
            task_date TEXT NOT NULL,
            is_done INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (goal_id) REFERENCES long_term_goals (id) ON DELETE SET NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_user_date ON tasks (user_id, task_date)"
    )


def initialize_database() -> None:
    """Create the database file (if needed) and all current tables."""
    conn = get_connection()
    try:
        create_users_table(conn)
        create_subjects_table(conn)
        create_study_sessions_table(conn)
        create_coding_logs_table(conn)
        create_goals_table(conn)
        create_snapshots_table(conn)
        create_long_term_goals_table(conn)
        create_tasks_table(conn)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    initialize_database()
    print("LifeOS database initialized at database/lifeos.db")
    print(
        "Tables ready: users, subjects, study_sessions, coding_logs, "
        "goals, snapshots, long_term_goals, tasks"
    )
