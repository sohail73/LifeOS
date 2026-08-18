"""
auth/auth_utils.py

Password hashing and user authentication helpers. Nothing in this
file touches Streamlit -- it's pure database + security logic so it
can be tested and reused independently of the UI.

Uses the `bcrypt` package directly (not passlib). passlib is
unmaintained and its bundled self-test breaks on newer bcrypt
releases (>=4.1), raising a confusing "password cannot be longer
than 72 bytes" error on the very first hash attempt. Calling bcrypt
directly avoids that entirely.
"""

from typing import Optional

import bcrypt

from config.database import get_connection

# bcrypt only uses the first 72 bytes of a password and raises an
# error on anything longer in recent versions -- truncate up front
# so long passwords behave predictably instead of crashing.
_MAX_PASSWORD_BYTES = 72


def _to_bcrypt_bytes(plain_password: str) -> bytes:
    return plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password with bcrypt. Never store the raw password."""
    hashed = bcrypt.hashpw(_to_bcrypt_bytes(plain_password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check a plain-text password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(plain_password), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed/unknown hash format -- treat as not matching.
        return False


def email_exists(email: str) -> bool:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def create_user(name: str, email: str, plain_password: str) -> Optional[int]:
    """
    Create a new user with a securely hashed password.
    Returns the new user's id, or None if the email is already taken.
    """
    email = email.strip().lower()
    name = name.strip()

    if email_exists(email):
        return None

    password_hash = hash_password(plain_password)

    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        # Every new user gets a default goals row so the dashboard
        # always has something sensible to compare against.
        conn.execute(
            "INSERT INTO goals (user_id) VALUES (?)", (cursor.lastrowid,)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def authenticate_user(email: str, plain_password: str) -> Optional[dict]:
    """
    Verify credentials. Returns a dict with the user's id/name/email
    on success, or None if the email or password is wrong. The two
    failure cases are intentionally indistinguishable to the caller.
    """
    email = email.strip().lower()

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    if not verify_password(plain_password, row["password_hash"]):
        return None

    return {"id": row["id"], "name": row["name"], "email": row["email"]}


def change_password(user_id: int, email: str, current_password: str, new_password: str) -> bool:
    """
    Verifies current_password is correct, then updates to new_password.
    Returns False (and changes nothing) if current_password is wrong.
    """
    if authenticate_user(email, current_password) is None:
        return False

    from database.queries import update_password_hash

    update_password_hash(user_id, hash_password(new_password))
    return True
