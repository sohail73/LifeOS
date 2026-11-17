"""
database/cloud_backup.py

Automatic backup of lifeos.db to a PRIVATE GitHub repository, plus
automatic restore when the hosting platform wipes the app's disk
(sleep / reboot / redeploy on Streamlit Community Cloud).

How it works
- Every commit that really changes data calls mark_dirty() (see
  config/database.py). about a minute later (debounced, so a burst of
  saves = one upload) the whole database is uploaded to the repo as
  one file. Every upload is a git commit, so GitHub keeps the full
  history of old versions for free.
- When the app process starts, initialize_database() calls
  restore_if_needed(): if the repo's copy differs from what this
  server last synced (or the server has no data), the repo's copy is
  restored first. Your accounts, passwords, roadmap, tasks -- all of it
  comes back exactly as it was.

Safety rules
- Nothing happens at all unless the secrets below are set, so running
  on localhost (PyCharm) is unaffected.
- If a backup exists but could not be restored (network/token
  problem), uploads are BLOCKED so a fresh empty database can never
  overwrite your real backup. The app tells you when this happens.
- A database with no accounts is never uploaded.

Secrets (Streamlit Cloud: App settings > Secrets), or environment vars:
    GITHUB_BACKUP_TOKEN  = "github_pat_..."   (fine-grained, ONE repo, Contents: read & write)
    GITHUB_BACKUP_REPO   = "yourname/lifeos-backup"
    GITHUB_BACKUP_BRANCH = "main"        (optional)
    GITHUB_BACKUP_PATH   = "lifeos.db"   (optional)
"""

import atexit
import base64
import hashlib
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone

import requests

from config.database import DB_PATH

API = "https://api.github.com"
DEBOUNCE_SECONDS = 120            # wait this long after a change before the first upload
DEFAULT_INTERVAL_MINUTES = 180    # minimum gap between uploads
EXIT_TIMEOUT = 8                  # seconds per request when flushing at shutdown
RETRY_SECONDS = 30
SIDECAR = DB_PATH.parent / ".cloud_backup_sha"  # remote file version this server last synced to

_lock = threading.RLock()
_cfg_cache = None
_state = {
    "checked": False,      # startup check/restore finished OK
    "restored": False,     # this process restored the DB from the repo
    "blocked": False,      # a backup exists but couldn't be restored -> never upload
    "suspend": False,      # True while we are writing a restored DB
    "timer": None,
    "dirty": False,        # changes exist that are not uploaded yet
    "due_at": None,        # time.time() of the next scheduled upload
    "last_upload_ts": None,  # time.time() of the last real upload
    "exiting": False,
    "next_retry": 0.0,
    "last_fp": None,       # fingerprint of the data at the last upload/restore
    "last_backup": None,   # datetime (UTC) of last successful upload
    "last_error": None,
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def _secret(name: str, default=None):
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        value = st.secrets.get(name)
        return value or default
    except Exception:
        return default


def _config():
    """Returns the config dict, or None when cloud backup isn't set up."""
    global _cfg_cache
    if _cfg_cache is not None:
        return _cfg_cache
    token, repo = _secret("GITHUB_BACKUP_TOKEN"), _secret("GITHUB_BACKUP_REPO")
    if not token or not repo:
        return None
    _cfg_cache = {
        "token": str(token).strip(),
        "repo": str(repo).strip().strip("/"),
        "branch": str(_secret("GITHUB_BACKUP_BRANCH", "main")).strip(),
        "path": str(_secret("GITHUB_BACKUP_PATH", "lifeos.db")).strip().strip("/"),
    }
    return _cfg_cache


def is_enabled() -> bool:
    return _config() is not None


def status() -> dict:
    return {
        "enabled": is_enabled(),
        "checked": _state["checked"],
        "restored": _state["restored"],
        "blocked": _state["blocked"],
        "last_backup": _state["last_backup"],
        "last_error": _state["last_error"],
        "pending": _state["dirty"],
        "next_backup_ts": _state["due_at"],
        "interval_minutes": _interval_seconds() // 60,
        "accounts": _user_count(),
    }


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------
def _t(normal: int) -> int:
    return EXIT_TIMEOUT if _state["exiting"] else normal


def _interval_seconds() -> int:
    try:
        minutes = int(float(_secret("GITHUB_BACKUP_INTERVAL_MINUTES", DEFAULT_INTERVAL_MINUTES)))
    except (TypeError, ValueError):
        minutes = DEFAULT_INTERVAL_MINUTES
    return max(1, minutes) * 60


def _headers(cfg, raw: bool = False) -> dict:
    return {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _file_url(cfg) -> str:
    return f"{API}/repos/{cfg['repo']}/contents/{cfg['path']}"


def _remote_sha(cfg):
    """Version id of the backup file in the repo, or None if the file doesn't exist yet.
    Raises if the repo/token is wrong (so a typo can't look like 'no backup yet')."""
    r = requests.get(_file_url(cfg), headers=_headers(cfg), params={"ref": cfg["branch"]}, timeout=_t(30))
    if r.status_code == 404:
        repo_check = requests.get(f"{API}/repos/{cfg['repo']}", headers=_headers(cfg), timeout=_t(30))
        if repo_check.status_code != 200:
            raise RuntimeError(
                f"Backup repo '{cfg['repo']}' not reachable (HTTP {repo_check.status_code}) -- "
                "check the repo name and that the token has access to it."
            )
        return None
    r.raise_for_status()
    return r.json()["sha"]


def _remote_download(cfg) -> bytes:
    r = requests.get(_file_url(cfg), headers=_headers(cfg, raw=True), params={"ref": cfg["branch"]}, timeout=_t(60))
    r.raise_for_status()
    return r.content


def _remote_upload(cfg, data: bytes, sha, note: str = "") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "message": f"LifeOS backup {stamp} UTC" + (f" (changed: {note})" if note else ""),
        "content": base64.b64encode(data).decode("ascii"),
        "branch": cfg["branch"],
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(_file_url(cfg), headers=_headers(cfg), json=payload, timeout=_t(60))
    r.raise_for_status()
    return r.json()["content"]["sha"]


# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------
def _user_count() -> int:
    if not DB_PATH.exists():
        return 0
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error:
        return 0


def _local_has_users() -> bool:
    return _user_count() > 0


def _fingerprint():
    """{table: hash of its rows}, ignoring snapshots.created_at (a refresh stamp).
    Returns None if it can't be computed (then we just upload, to be safe)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            result = {}
            tables = [
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]
            for table in tables:
                cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]
                if table == "snapshots":
                    cols = [c for c in cols if c != "created_at"]
                digest = hashlib.sha256()
                column_sql = ", ".join(f'"{c}"' for c in cols)
                for row in conn.execute(f'SELECT {column_sql} FROM "{table}" ORDER BY rowid'):
                    digest.update(repr(row).encode())
                result[table] = digest.hexdigest()
            return result
        finally:
            conn.close()
    except Exception:
        return None


def _changed_tables(old, new) -> str:
    if not new:
        return "unknown"
    if not old:
        return "first backup since app start"
    changed = sorted(t for t in new if new.get(t) != old.get(t))
    return ", ".join(changed) if changed else "none"


def _read_sidecar():
    try:
        return SIDECAR.read_text().strip() or None
    except OSError:
        return None


def _write_sidecar(sha: str) -> None:
    try:
        SIDECAR.write_text(sha)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Restore (runs when the app process starts)
# ---------------------------------------------------------------------------
def restore_if_needed() -> None:
    cfg = _config()
    if cfg is None:
        return

    from database.backup_tools import restore_from_bytes

    with _lock:
        if _state["checked"] or time.time() < _state["next_retry"]:
            return
        try:
            remote_sha = _remote_sha(cfg)

            if remote_sha is None:
                # No backup in the repo yet. Fine -- first upload happens on the next save.
                _state.update(checked=True, blocked=False, last_error=None)
                if _local_has_users():
                    mark_dirty()
                return

            if _read_sidecar() == remote_sha and _local_has_users():
                # This server's data is exactly what the repo has (or newer). Keep it.
                _state.update(checked=True, blocked=False, last_error=None)
                return

            data = _remote_download(cfg)
            _state["suspend"] = True
            try:
                ok, message = restore_from_bytes(data)
            finally:
                _state["suspend"] = False
            if not ok:
                raise RuntimeError(message)

            _write_sidecar(remote_sha)
            _state.update(checked=True, restored=True, blocked=False, last_error=None, last_fp=_fingerprint())
        except Exception as exc:
            _state.update(
                blocked=True,
                last_error=f"Could not restore your backup: {exc}",
                next_retry=time.time() + RETRY_SECONDS,
            )


# ---------------------------------------------------------------------------
# Backup (runs after saves)
# ---------------------------------------------------------------------------
def mark_dirty() -> None:
    """Called after a commit that changed data. Makes sure ONE upload is scheduled:
    ~2 minutes from now if nothing was uploaded recently, otherwise as soon as the
    minimum gap since the last upload has passed."""
    if _state["suspend"] or _state["blocked"] or not is_enabled():
        return
    with _lock:
        _state["dirty"] = True
        timer = _state["timer"]
        if timer is not None and timer.is_alive():
            return
        now = time.time()
        delay = DEBOUNCE_SECONDS
        last = _state["last_upload_ts"]
        if last is not None:
            delay = max(DEBOUNCE_SECONDS, last + _interval_seconds() - now)
        _state["due_at"] = now + delay
        timer = threading.Timer(delay, _timer_fire)
        timer.daemon = True
        _state["timer"] = timer
        timer.start()


def _timer_fire() -> None:
    with _lock:
        _state["timer"] = None  # so saves during the upload schedule the next one
        _state["due_at"] = None
    backup_now()


def backup_now():
    """Upload the database now. Returns (ok, message)."""
    cfg = _config()
    if cfg is None:
        return False, "Cloud backup is not configured."
    if _state["blocked"]:
        return False, "Uploads are paused because your existing backup could not be restored."

    from database.backup_tools import make_backup_bytes, validate_backup

    with _lock:
        try:
            data = make_backup_bytes()
            ok, message = validate_backup(data)
            if not ok:
                return False, f"Skipped: {message}"
            fingerprint = _fingerprint()
            if fingerprint is not None and fingerprint == _state["last_fp"]:
                _state["dirty"] = False
                return True, "Nothing new to back up -- the cloud copy is already up to date."
            note = _changed_tables(_state["last_fp"], fingerprint)
            new_sha = _remote_upload(cfg, data, _remote_sha(cfg), note)
            _write_sidecar(new_sha)
            _state["last_fp"] = fingerprint
            _state["dirty"] = False
            _state["last_upload_ts"] = time.time()
            _state["last_backup"] = datetime.now(timezone.utc)
            _state["last_error"] = None
            return True, "Backup uploaded."
        except Exception as exc:
            _state["last_error"] = f"Backup failed: {exc}"
            return False, _state["last_error"]


def _flush_on_exit() -> None:
    """Best effort when the app stops normally: upload changes still waiting for their slot."""
    try:
        if _state["dirty"] and not _state["blocked"] and is_enabled():
            _state["exiting"] = True
            backup_now()
    except Exception:
        pass


atexit.register(_flush_on_exit)
