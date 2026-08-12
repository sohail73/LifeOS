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

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
