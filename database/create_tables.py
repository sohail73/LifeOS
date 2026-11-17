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


def create_career_milestones_table(conn) -> None:
    # A roadmap entry for an internship, placement, hackathon,
    # competition, or job -- a target you're aiming for by a certain
    # date. Kept separate from long_term_goals (which is about daily
    # study tasks) since a milestone here is a single target, not a
    # day-by-day schedule.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS career_milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            milestone_type TEXT NOT NULL,
            title TEXT NOT NULL,
            target_date TEXT,
            status TEXT NOT NULL DEFAULT 'Upcoming',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )


def create_reward_milestones_table(conn) -> None:
    # A personal reward ladder: "once I reach X, I'll do/buy Y".
    # trigger_value is optional and only used to sort the ladder
    # (e.g. 10, 20, 30 for LPA figures) -- the label is what's shown.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            milestone_label TEXT NOT NULL,
            trigger_value REAL,
            reward_description TEXT NOT NULL,
            is_achieved INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )


def create_job_targets_table(conn) -> None:
    # Which job(s) the user is aiming for: Ready (qualified now),
    # In Progress (working toward it, usually via a linked long-term
    # goal -- see job_target_goals below), or Future (something to
    # aim for later). Mirrors the projects table's status pattern.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            company TEXT,
            status TEXT NOT NULL DEFAULT 'Future',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )


def create_job_target_goals_table(conn) -> None:
    # Many-to-many: an "In Progress" job target can be tracked by one
    # or more long-term goals; when every linked goal reaches 100%
    # completion, the job target auto-promotes to "Ready" (see
    # analytics/goal_maintenance.py), same pattern as project_goals.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_target_goals (
            job_target_id INTEGER NOT NULL,
            goal_id INTEGER NOT NULL,
            PRIMARY KEY (job_target_id, goal_id),
            FOREIGN KEY (job_target_id) REFERENCES job_targets (id) ON DELETE CASCADE,
            FOREIGN KEY (goal_id) REFERENCES long_term_goals (id) ON DELETE CASCADE
        )
        """
    )


def create_career_notes_table(conn) -> None:
    # A free-form scratchpad for the Career page -- "remember to do X
    # later", "this job needs one more goal I haven't created yet",
    # or literally anything else worth jotting down and not losing
    # track of. Deliberately unstructured (just text + a done flag).
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS career_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            is_done INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )


def create_roadmap_steps_table(conn) -> None:
    # A sequential learning path -- "Data Science, then DL, then
    # MLOps, then Cloud, then AWS, then LLM, then RAG" -- rendered as
    # a flowchart on the Career page. order_index controls the
    # sequence; status is Ready (done) / In Progress (running) /
    # Future (not started), same vocabulary as job_targets.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS roadmap_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Future',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )


def create_roadmap_step_goals_table(conn) -> None:
    # Many-to-many: a roadmap step can be tracked by one or more
    # long-term goals; when all linked goals hit 100%, the step
    # auto-promotes to "Ready" (see analytics/goal_maintenance.py),
    # same pattern as job_target_goals.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS roadmap_step_goals (
            step_id INTEGER NOT NULL,
            goal_id INTEGER NOT NULL,
            PRIMARY KEY (step_id, goal_id),
            FOREIGN KEY (step_id) REFERENCES roadmap_steps (id) ON DELETE CASCADE,
            FOREIGN KEY (goal_id) REFERENCES long_term_goals (id) ON DELETE CASCADE
        )
        """
    )


def create_gym_sessions_table(conn) -> None:
    # A workout log -- date, type of workout (Push/Pull/Legs/Cardio/
    # etc.), how long, and freeform notes (exercises, sets/reps, how
    # it felt). Same shape as study_sessions, just for the gym.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gym_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            workout_type TEXT NOT NULL,
            duration_minutes REAL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gym_sessions_user_date ON gym_sessions (user_id, date)"
    )


def create_job_roles_table(conn) -> None:
    # A job role you're building toward ("Data Scientist", "AI Engineer"). It has no
    # status of its own: it is "ready" automatically once every roadmap step attached
    # to it (job_role_steps below) is Ready.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )


def create_job_role_steps_table(conn) -> None:
    # Many-to-many: which roadmap steps a job role needs. One step can feed several
    # roles (e.g. "Python" counts toward both Data Scientist and AI Engineer).
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_role_steps (
            role_id INTEGER NOT NULL,
            step_id INTEGER NOT NULL,
            PRIMARY KEY (role_id, step_id),
            FOREIGN KEY (role_id) REFERENCES job_roles (id) ON DELETE CASCADE,
            FOREIGN KEY (step_id) REFERENCES roadmap_steps (id) ON DELETE CASCADE
        )
        """
    )


def create_leave_days_table(conn) -> None:
    # Days the user was away / couldn't log anything (travel, sick, family
    # function...). A leave day never breaks a streak and is drawn in blue
    # on the streak heatmaps. Purely additive -- no existing table changes.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS leave_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            leave_date TEXT NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (user_id, leave_date)
        )
        """
    )


def create_calendar_events_table(conn) -> None:
    # Things the user wants on their calendar: internships, interviews,
    # applications, exams, hackathons, deadlines... A one-day event has
    # end_date = start_date; a multi-day one (e.g. a 2-month internship)
    # spans start_date..end_date. Purely additive -- no existing table changes.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Other',
            company TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_calendar_events_user_start "
        "ON calendar_events (user_id, start_date)"
    )


def initialize_database() -> None:
    """Create the database file (if needed), all current tables, and
    apply any column migrations needed for databases created by an
    earlier version of LifeOS.

    If cloud backup is configured (hosted app), the last backup is
    restored first when this server's disk was wiped -- see
    database/cloud_backup.py. On localhost this does nothing."""
    from database import cloud_backup

    cloud_backup.restore_if_needed()

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
        create_career_milestones_table(conn)
        create_reward_milestones_table(conn)
        create_job_targets_table(conn)
        create_job_target_goals_table(conn)
        create_career_notes_table(conn)
        create_roadmap_steps_table(conn)
        create_roadmap_step_goals_table(conn)
        create_job_roles_table(conn)
        create_job_role_steps_table(conn)
        create_gym_sessions_table(conn)
        create_leave_days_table(conn)
        create_calendar_events_table(conn)
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
    # Priority so the Dashboard can show "do this first, then this,
    # then this" -- 1 = High, 2 = Medium (default), 3 = Low. Lives on
    # the task itself for standalone tasks (no goal); a task linked
    # to a long-term goal instead inherits the goal's priority below,
    # so setting it once on the goal covers every day's task under
    # it -- no need to re-set it daily.
    _ensure_column(conn, "tasks", "priority", "INTEGER NOT NULL DEFAULT 2")
    _ensure_column(conn, "long_term_goals", "priority", "INTEGER NOT NULL DEFAULT 2")
    # Manual ordering within a day's same-priority tasks (the "move
    # up/down" buttons). Existing rows are backfilled with their own
    # id so today's creation order is preserved exactly; new tasks get
    # max+1 for their date (see queries.add_task).
    # roadmap_steps: parallel tracks. Each lane is its own chain of steps
    # (e.g. lane 1 = Data Science -> DL -> MLOps, lane 2 = Java -> Spring),
    # drawn side by side; order_index is now the position within a lane.
    _ensure_column(conn, "roadmap_steps", "lane", "INTEGER NOT NULL DEFAULT 1")
    # long_term_goals: manual order among goals of the same priority (the
    # Up/Down buttons on a goal card). 0 = never reordered, in which case
    # goals fall back to newest-start-first exactly like before. Tasks
    # under a goal follow this order every day, so it's set once here.
    _ensure_column(conn, "long_term_goals", "goal_order", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "tasks", "task_order", "INTEGER NOT NULL DEFAULT 0")
    conn.execute("UPDATE tasks SET task_order = id WHERE task_order = 0")

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

    # job_targets: an optional deadline ("crack this job by 30 Jan") so
    # the Career page can show a countdown / how much time is left.
    _ensure_column(conn, "job_targets", "deadline", "TEXT")
    # job_targets: optional package/CTC label (e.g. "5 LPA") shown
    # alongside the title, and a "pinned" flag -- at most one job
    # target can be pinned to show its countdown on the Dashboard.
    _ensure_column(conn, "job_targets", "target_package", "TEXT")
    _ensure_column(conn, "job_targets", "is_pinned", "INTEGER NOT NULL DEFAULT 0")


if __name__ == "__main__":
    initialize_database()
    print("LifeOS database initialized at database/lifeos.db")
    print(
        "Tables ready: users, subjects, study_sessions, coding_logs, goals, "
        "snapshots, long_term_goals, tasks, languages, projects, future_topics, "
        "known_skills, project_goals, project_future_topics, career_milestones, "
        "reward_milestones, job_targets, job_target_goals, career_notes, "
        "roadmap_steps, roadmap_step_goals, gym_sessions, job_roles, job_role_steps"
    )
