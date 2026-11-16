"""
auth/session.py

Thin wrapper around st.session_state for tracking who's logged in.
This is the ONLY place in the app that should read/write the
"user_*" session_state keys directly -- every page imports these
helpers instead of touching st.session_state itself.

st.session_state alone is wiped when the browser tab is closed, so
"Keep me logged in" adds a browser cookie holding a random token
(see auth/remember_tokens.py). Next visit, sync_browser_cookie() reads
the cookie and logs you straight in. The cookie is read, written and
cleared inside the browser by a tiny component (auth/cookie_bridge.py),
because Streamlit Cloud doesn't reliably pass JS-set cookies to the server.
"""

import secrets

import streamlit as st

from auth import cookie_bridge, remember_tokens
from config import timezone as _timezone  # noqa: F401  (sets the app to IST on import)

COOKIE_NAME = "lifeos_session"
KEEP_LOGIN_VERSION = "v3"


def _log(event: str) -> None:
    """Remember the last few keep-login events (shown in the sidebar status panel)."""
    log = st.session_state.setdefault("_kl_log", [])
    log.append(event)
    del log[:-10]


def _cookie_token():
    """The login token the browser sent when this session started (None if none/unsupported)."""
    try:
        return st.context.cookies.get(COOKIE_NAME)
    except Exception:
        return None


def login(user: dict, remember: bool = False) -> None:
    """Store the authenticated user in session state. With remember=True this
    device also stays logged in (cookie) for TOKEN_DAYS days."""
    st.session_state["user_id"] = user["id"]
    st.session_state["user_name"] = user["name"]
    st.session_state["user_email"] = user["email"]
    st.session_state["_auto_login_tried"] = True

    if remember:
        try:
            token = remember_tokens.create_token(user["id"])
            st.session_state["_remember_token"] = token
            st.session_state["_cookie_action"] = ("set", token)
            _log("login: 'keep me logged in' ticked, token saved in the database")
        except Exception as exc:  # never block a normal login, but say what went wrong
            _log(f"login: token could NOT be saved ({type(exc).__name__}: {exc})")
    else:
        _log("login: 'keep me logged in' NOT ticked")


def _diag_raw() -> str:
    return st.session_state.get("_login_diag", "not checked yet")


def login_diag() -> str:
    """Short human-readable result of the last saved-login check (shown on the login page)."""
    return f"{_diag_raw()} [keep-login {KEEP_LOGIN_VERSION}]"


def _queue_bridge(action: str, value: str = "") -> None:
    st.session_state["_bridge_args"] = {"action": action, "value": value, "nonce": secrets.token_hex(4)}


def _finish_auto_login(token: str) -> None:
    """Decide the saved-login check with the cookie value found (empty = none)."""
    st.session_state["_auto_login_tried"] = True
    try:
        user = remember_tokens.user_for_token(token)
    except Exception:
        user = None

    if user is not None:
        st.session_state["user_id"] = user["id"]
        st.session_state["user_name"] = user["name"]
        st.session_state["user_email"] = user["email"]
        st.session_state["_remember_token"] = token  # so Log Out can delete exactly this token
        st.session_state["_login_diag"] = "logged in from saved login"
    elif token:
        st.session_state["_login_diag"] = "saved login found but expired or unknown"
    else:
        st.session_state["_login_diag"] = "no saved login in this browser"


def _sync_browser_cookie() -> None:
    """Call once, near the top of every page (require_login() does it for you).

    - Writes/clears the "keep me logged in" cookie requested by login()/logout().
    - If nobody is logged in yet, looks for a saved-login cookie and logs in with it.

    All cookie work happens in the browser through a tiny component (auth/cookie_bridge.py);
    its answer arrives as a rerun, so nothing here blocks. Never writes to the database."""
    action = st.session_state.pop("_cookie_action", None)
    if action:
        kind, token = action
        _queue_bridge("set" if kind == "set" else "clear", token or "")
        _log(f"asked the browser to {'store' if kind == 'set' else 'remove'} the login cookie")
    elif (
        st.session_state.get("_bridge_args") is None
        and not is_logged_in()
        and not st.session_state.get("_auto_login_tried")
    ):
        server_token = _cookie_token()  # fast path: works when the server does see the cookie (e.g. localhost)
        if server_token:
            _log("server received the login cookie directly")
            _finish_auto_login(server_token)
        else:
            _queue_bridge("get")
            _log("asked the browser if it has a saved login cookie")

    args = st.session_state.get("_bridge_args")
    if not args:
        return

    max_age = 60 * 60 * 24 * remember_tokens.TOKEN_DAYS if args["action"] == "set" else 0
    try:
        reply = cookie_bridge.cookie_op(COOKIE_NAME, args["action"], args["value"], max_age, args["nonce"])
    except Exception as exc:
        _log(f"browser component FAILED to start ({type(exc).__name__}: {exc})")
        st.session_state["_bridge_args"] = None
        if args["action"] == "get":
            _finish_auto_login("")
            st.session_state["_login_diag"] = f"browser cookie check failed ({type(exc).__name__})"
        else:
            st.toast(f"Keep-login could not be saved ({type(exc).__name__}: {exc})", icon="⚠️")
        return

    if not (isinstance(reply, dict) and reply.get("nonce") == args["nonce"]):
        if args["action"] == "get":
            st.session_state["_login_diag"] = "checking the browser..."
        if st.session_state.get("_kl_waiting") != args["nonce"]:
            st.session_state["_kl_waiting"] = args["nonce"]
            _log(f"waiting for the browser to answer ({args['action']})")
        return  # browser hasn't answered yet; its answer triggers a rerun

    st.session_state["_bridge_args"] = None
    _log(
        f"browser answered: {args['action']}, ok={reply.get('ok')}, "
        f"cookie present in browser={bool(reply.get('value'))}"
    )
    if args["action"] == "get":
        _finish_auto_login(reply.get("value") or "")
    elif args["action"] == "set":
        if reply.get("ok"):
            st.toast("Keep-login is on: this browser will remember you.", icon="✅")
        else:
            st.toast("Keep-login failed: your browser refused to store the cookie.", icon="⚠️")


def _render_status_panel() -> None:
    """Small sidebar panel with the keep-login steps. Never allowed to break a page."""
    try:
        with st.sidebar.expander(f"Keep-login status ({KEEP_LOGIN_VERSION})"):
            st.caption(f"Logged in: {'yes' if is_logged_in() else 'no'}")
            st.caption(f"Saved-login check: {_diag_raw()}")
            for line in st.session_state.get("_kl_log", []) or ["(nothing yet)"]:
                st.caption(f"- {line}")
    except Exception:
        pass


def sync_browser_cookie() -> None:
    """See _sync_browser_cookie(); this wrapper also draws the sidebar status panel."""
    try:
        _sync_browser_cookie()
    finally:
        _render_status_panel()


def flush_cookie_actions() -> None:
    """Kept so older callers keep working; sync_browser_cookie() does the work."""
    return None


try_auto_login = sync_browser_cookie  # old name, same behaviour


def logout() -> None:
    """Log out and make this device forget the login (token deleted + cookie cleared)."""
    for raw in {st.session_state.get("_remember_token"), _cookie_token()}:
        try:
            remember_tokens.delete_token(raw)
        except Exception:
            pass
    for key in (
        "user_id", "user_name", "user_email", "snapshots_ensured_date",
        "goal_maintenance_date", "_remember_token",
    ):
        st.session_state.pop(key, None)
    st.session_state["_cookie_action"] = ("clear", None)
    st.session_state["_auto_login_tried"] = True  # don't auto-login again in this session


def is_logged_in() -> bool:
    return st.session_state.get("user_id") is not None


def current_user_id() -> int:
    return st.session_state["user_id"]


def current_user_name() -> str:
    return st.session_state.get("user_name", "")


def current_user_email() -> str:
    return st.session_state.get("user_email", "")


def require_login() -> None:
    """
    Call at the top of every page (except the main login/signup page).
    Stops rendering and prompts the user to log in if there's no
    active session. Also runs two once-per-day-per-session
    maintenance checks:

    - Refreshes this user's weekly/monthly/yearly snapshots for the
      CURRENT period (analytics.snapshot.ensure_current_snapshots) --
      see that module for why an on-visit refresh is how "automatic"
      snapshots work in an app with no background scheduler.
    - Auto-shifts any goal whose schedule fell behind (a task's date
      passed without being marked done) and shows a toast for any
      goal that starts today (analytics.goal_maintenance).
    """
    sync_browser_cookie()

    if not is_logged_in() and _diag_raw().startswith("checking"):
        st.info("Checking your saved login... If this stays here, open the main page and log in.")
        st.stop()

    if not is_logged_in():
        st.warning("Please log in to view this page.")
        st.info("Head back to the **LifeOS** main page to log in or create an account.")
        st.stop()

    from datetime import date

    today_str = date.today().isoformat()
    if st.session_state.get("snapshots_ensured_date") != today_str:
        from analytics.snapshot import ensure_current_snapshots

        try:
            ensure_current_snapshots(current_user_id())
        except Exception:
            # Snapshot refresh is a nice-to-have -- never let it block
            # the actual page the user came here for.
            pass
        st.session_state["snapshots_ensured_date"] = today_str

    if st.session_state.get("goal_maintenance_date") != today_str:
        from analytics.goal_maintenance import auto_shift_overdue_tasks, get_goals_starting_today

        try:
            shifted = auto_shift_overdue_tasks(current_user_id())
            for item in shifted:
                st.toast(
                    f"⏳ '{item['goal_title']}' had a missed task -- its whole schedule moved "
                    f"forward {item['shift_days']} day(s). New end date: {item['new_end_date']}.",
                    icon="⏳",
                )

            starting = get_goals_starting_today(current_user_id())
            for goal in starting:
                st.toast(f"🚀 '{goal['title']}' starts today!", icon="🚀")
        except Exception:
            # Same reasoning as above -- this is a nice-to-have, never
            # let it block the page the user actually came here for.
            pass
        st.session_state["goal_maintenance_date"] = today_str
