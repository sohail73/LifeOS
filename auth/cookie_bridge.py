"""
auth/cookie_bridge.py

Reads a browser cookie from inside the browser (see
cookie_bridge_frontend/index.html) and hands it to Python.

read_cookie() returns None while the browser hasn't answered yet; once it
has, it returns {"value": "<cookie value or empty string>"}. The answer
arrives as a normal Streamlit rerun, so callers just call it again.
"""

from pathlib import Path

import streamlit.components.v1 as components

_FRONTEND_DIR = Path(__file__).resolve().parent / "cookie_bridge_frontend"
_component = None


def read_cookie(name: str):
    global _component
    if _component is None:
        _component = components.declare_component("lifeos_cookie_bridge", path=str(_FRONTEND_DIR))
    return _component(name=name, key="lifeos_cookie_bridge_read", default=None)
