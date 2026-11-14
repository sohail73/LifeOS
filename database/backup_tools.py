"""
database/backup_tools.py

Manual backup / restore of the whole LifeOS SQLite database.

- make_backup_bytes(): a consistent snapshot of the live DB as bytes
  (uses SQLite's own backup API, so it is safe even while the app is
  being used).
- validate_backup(): checks that an uploaded file really is a LifeOS
  database before anything is touched.
- restore_from_bytes(): replaces the live DB's contents with an
  uploaded backup. A safety copy of the current DB is kept first.

The database holds EVERY user's data, so the UI only offers these to
the owner account (see is_owner()).
"""

import os
import sqlite3
import tempfile
from pathlib import Path

from config.database import DB_PATH, get_connection

SAFETY_COPY_PATH = DB_PATH.parent / "lifeos_before_restore.db"
REQUIRED_TABLES = {"users", "study_sessions", "tasks"}


def is_owner(user_id: int, email: str) -> bool:
    """True if this account may download/restore the database.

    If ADMIN_EMAIL is set in Streamlit secrets, only that email. Otherwise
    the first account ever created (lowest user id) is the owner.
    """
    try:
        import streamlit as st

        admin_email = st.secrets.get("ADMIN_EMAIL")
    except Exception:
        admin_email = None

    if admin_email:
        return (email or "").strip().lower() == str(admin_email).strip().lower()

    conn = get_connection()
    try:
        row = conn.execute("SELECT MIN(id) AS first_id FROM users").fetchone()
        return row is not None and row["first_id"] == user_id
    finally:
        conn.close()


def make_backup_bytes() -> bytes:
    """Consistent snapshot of the live database, as raw .db bytes."""
    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        src = get_connection()
        dst = sqlite3.connect(tmp_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        return Path(tmp_path).read_bytes()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def validate_backup(data: bytes):
    """Returns (ok, message). Never touches the live database."""
    if not data or not data.startswith(b"SQLite format 3\x00"):
        return False, "This is not a SQLite database file."

    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        Path(tmp_path).write_bytes(data)
        conn = sqlite3.connect(tmp_path)
        try:
            check = conn.execute("PRAGMA integrity_check").fetchone()
            if not check or check[0] != "ok":
                return False, "The file is damaged (integrity check failed)."
            tables = {
                r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            missing = REQUIRED_TABLES - tables
            if missing:
                return False, f"Not a LifeOS backup (missing tables: {', '.join(sorted(missing))})."
            users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if users == 0:
                return False, "This backup has no accounts in it, so it was not restored."
            return True, f"Valid LifeOS backup with {users} account(s)."
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        return False, f"Could not read the file: {exc}"
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def restore_from_bytes(data: bytes):
    """Replace the live DB's contents with the uploaded backup.

    Returns (ok, message). The current DB is saved to
    database/lifeos_before_restore.db first.
    """
    ok, message = validate_backup(data)
    if not ok:
        return False, message

    try:
        SAFETY_COPY_PATH.write_bytes(make_backup_bytes())
    except Exception as exc:  # don't restore if we can't keep a safety copy
        return False, f"Could not save a safety copy first, so nothing was changed ({exc})."

    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        Path(tmp_path).write_bytes(data)
        src = sqlite3.connect(tmp_path)
        dst = get_connection()
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
            src.close()
    except Exception as exc:
        return False, f"Restore failed ({exc}). Your previous data is saved in {SAFETY_COPY_PATH.name}."
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    return True, "Backup restored."
