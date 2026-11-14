"""
auth/remember_tokens.py

"Keep me logged in" tokens -- pure database logic (no Streamlit here).

How it works: when you log in with "Keep me logged in" ticked, a long
random token is created. The BROWSER keeps the token (in a cookie); the
DATABASE keeps only its SHA-256 hash, so a leaked database/backup can't
be used to log in. When you come back, the app looks the token up,
and if it exists and hasn't expired you are logged in without typing a
password. Logging out deletes the token.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from config.database import get_connection

TOKEN_DAYS = 30           # how long a device stays logged in
MAX_TOKENS_PER_USER = 10  # oldest devices are dropped beyond this


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_token(user_id: int, days: int = TOKEN_DAYS) -> str:
    """Create a login token for this user and return the RAW token (store it in the cookie only)."""
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=days)).isoformat()

    conn = get_connection()
    try:
        conn.execute("DELETE FROM login_tokens WHERE expires_at < ?", (now.isoformat(),))
        conn.execute(
            "INSERT INTO login_tokens (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (_hash(raw_token), user_id, expires_at),
        )
        conn.execute(
            """
            DELETE FROM login_tokens
            WHERE user_id = ?
              AND token_hash NOT IN (
                  SELECT token_hash FROM login_tokens
                  WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?
              )
            """,
            (user_id, user_id, MAX_TOKENS_PER_USER),
        )
        conn.commit()
    finally:
        conn.close()
    return raw_token


def user_for_token(raw_token):
    """Returns {"id","name","email"} for a valid, unexpired token, else None. Never writes."""
    if not raw_token or not isinstance(raw_token, str) or len(raw_token) > 200:
        return None
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT u.id, u.name, u.email, t.expires_at
            FROM login_tokens t JOIN users u ON u.id = t.user_id
            WHERE t.token_hash = ?
            """,
            (_hash(raw_token),),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    try:
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            return None
    except ValueError:
        return None
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


def delete_token(raw_token) -> None:
    if not raw_token or not isinstance(raw_token, str):
        return
    conn = get_connection()
    try:
        conn.execute("DELETE FROM login_tokens WHERE token_hash = ?", (_hash(raw_token),))
        conn.commit()
    finally:
        conn.close()
