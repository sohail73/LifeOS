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


def create_languages_table(conn) -> None:
    # User-managed list of coding languages for the Coding Tracker,
    # same pattern as subjects: seeded with common defaults, but the
    # user can add anything not in that list (e.g. "Pandas").
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS languages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (user_id, name)
        )
        """
    )


def create_projects_table(conn) -> None:
    # Future/planned projects the user wants to track -- idea, tech
    # stack, status, target date, and free-form notes.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'Planned',
            tech_stack TEXT,
            target_date TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )


def create_future_topics_table(conn) -> None:
    # A lightweight "someday/maybe" list of things to study later --
    # not tied to a date or a goal, unlike tasks/long_term_goals.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS future_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )


def create_known_skills_table(conn) -> None:
    # A flat "what I already know" list -- simpler than Projects'
    # Ready/In Progress/Planned system, just things you can already do.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS known_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (user_id, name)
        )
        """
    )


def create_project_goals_table(conn) -> None:
    # Many-to-many: an "In Progress" project can be tracked by several
    # long-term goals; when every linked goal reaches 100% completion,
    # the project auto-promotes to "Ready" (see analytics/goal_maintenance.py).
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_goals (
            project_id INTEGER NOT NULL,
            goal_id INTEGER NOT NULL,
            PRIMARY KEY (project_id, goal_id),
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (goal_id) REFERENCES long_term_goals (id) ON DELETE CASCADE
        )
        """
    )


def create_project_future_topics_table(conn) -> None:
    # Many-to-many: a "Planned" (future) project can reference one or
    # more items from the Future Topics wishlist.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_future_topics (
            project_id INTEGER NOT NULL,
            future_topic_id INTEGER NOT NULL,
            PRIMARY KEY (project_id, future_topic_id),
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (future_topic_id) REFERENCES future_topics (id) ON DELETE CASCADE
        )
        """
    )


def initialize_database() -> None:
    """Create the database file (if needed), all current tables, and
    apply any column migrations needed for databases created by an
    earlier version of LifeOS."""
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
        create_languages_table(conn)
        create_projects_table(conn)
        create_future_topics_table(conn)
        create_known_skills_table(conn)
        create_project_goals_table(conn)
        create_project_future_topics_table(conn)
        _run_migrations(conn)
        conn.commit()
    finally:
        conn.close()


def _ensure_column(conn, table: str, column: str, coltype: str) -> None:
    """Add `column` to `table` if it doesn't already exist. SQLite's
    ALTER TABLE only supports adding columns, which is exactly what
    the migrations below need -- existing databases (created before a
    feature was added) get the new column with a safe default instead
    of breaking on the next query that references it."""
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def _run_migrations(conn) -> None:
    # users: LeetCode profile link + optional profile picture (both nullable/opt-in).
    _ensure_column(conn, "users", "leetcode_username", "TEXT")
    _ensure_column(conn, "users", "avatar_base64", "TEXT")
    _ensure_column(conn, "users", "custom_quote", "TEXT")

    # coding_logs: track where an entry came from and dedupe LeetCode syncs.
    _ensure_column(conn, "coding_logs", "source", "TEXT NOT NULL DEFAULT 'manual'")
    _ensure_column(conn, "coding_logs", "external_id", "TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_coding_logs_user_external "
        "ON coding_logs (user_id, external_id) WHERE external_id IS NOT NULL"
    )

    # tasks: remember which study_sessions row was auto-created when a
    # task was marked complete (so un-completing cleans up after
    # itself), and an optional planned time window (e.g. 6-7 PM) used
    # to pre-fill the duration when the task is completed.
    _ensure_column(conn, "tasks", "linked_session_id", "INTEGER")
    _ensure_column(conn, "tasks", "planned_start_time", "TEXT")
    _ensure_column(conn, "tasks", "planned_end_time", "TEXT")

    # projects: optionally link a "Ready"/"In Progress"/etc. aspiration
    # to the long-term goal actively tracking progress toward it. This
    # single-column link has been superseded by the project_goals
    # many-to-many table (a project can now track several goals), but
    # the column is kept and migrated below so older databases don't
    # lose data.
    _ensure_column(conn, "projects", "linked_goal_id", "INTEGER")
    conn.execute(
        """
        INSERT OR IGNORE INTO project_goals (project_id, goal_id)
        SELECT id, linked_goal_id FROM projects WHERE linked_goal_id IS NOT NULL
        """
    )


if __name__ == "__main__":
    initialize_database()
    print("LifeOS database initialized at database/lifeos.db")
    print(
        "Tables ready: users, subjects, study_sessions, coding_logs, goals, "
        "snapshots, long_term_goals, tasks, languages, projects, future_topics, "
        "known_skills, project_goals, project_future_topics"
    )
