"""
auth/cookie_bridge.py

Reads / writes / clears a browser cookie from inside the browser (see
cookie_bridge_frontend/index.html) and hands the result to Python.

cookie_op() returns None until the browser has answered, then
{"value": <cookie value after the operation>, "nonce": ..., "action": ..., "ok": bool}.
The answer arrives as a normal Streamlit rerun.
"""

from pathlib import Path

import streamlit.components.v1 as components

_FRONTEND_DIR = Path(__file__).resolve().parent / "cookie_bridge_frontend"
_component = None


def cookie_op(name: str, action: str, value: str, max_age: int, nonce: str):
    """action: "get", "set" or "clear". The nonce makes every request unique."""
    global _component
    if _component is None:
        _component = components.declare_component("lifeos_cookie_bridge", path=str(_FRONTEND_DIR))
    return _component(
        name=name,
        action=action,
        value=value,
        max_age=max_age,
        nonce=nonce,
        key=f"lifeos_cookie_{nonce}",
        default=None,
    )
