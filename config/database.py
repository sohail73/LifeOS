"""
config/database.py

Central place for connecting to the LifeOS SQLite database.
Every other module (auth, analytics, widgets, etc.) should import
get_connection() from here instead of opening sqlite3 connections
on its own. This keeps the database layer swappable later
(e.g. migrating to PostgreSQL) without touching the rest of the app.
"""

import sqlite3
from pathlib import Path

# database/lifeos.db, resolved relative to this file so it works
# no matter what directory the app is launched from.
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "lifeos.db"


class _TrackedConnection(sqlite3.Connection):
    """A normal SQLite connection that tells the cloud-backup module
    whenever a commit actually changed data (rows inserted/updated/
    deleted). Read-only commits are ignored. If cloud backup isn't
    configured (e.g. running on localhost) this does nothing."""

    _noted_changes = 0

    def _note_changes(self) -> None:
        try:
            if self.total_changes > self._noted_changes:
                self._noted_changes = self.total_changes
                from database import cloud_backup

                cloud_backup.mark_dirty()
        except Exception:
            # Backup is a safety net -- it must never break a normal save.
            pass

    def commit(self) -> None:
        super().commit()
        self._note_changes()

    def __exit__(self, *args):
        result = super().__exit__(*args)
        self._note_changes()
        return result


def get_connection() -> sqlite3.Connection:
    """
    Open a connection to the LifeOS SQLite database.

    - Creates the database/ folder and the .db file automatically
      if they don't exist yet (no manual setup required).
    - Enables foreign key constraint enforcement (off by default in SQLite).
    - Uses sqlite3.Row so query results can be accessed like dicts
      (row["column_name"]) as well as by index.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, factory=_TrackedConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
