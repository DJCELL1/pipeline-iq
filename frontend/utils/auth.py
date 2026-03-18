"""
Auth helpers — no login required. Always returns the default admin user.
"""
import streamlit as st


def get_user() -> dict:
    return st.session_state.get("user", {
        "id": 1,
        "name": "Hardware Direct",
        "email": "admin@hardwaredirect.com.au",
        "role": "admin",
    })


def get_role() -> str:
    return get_user().get("role", "admin")


def has_role(*roles: str) -> bool:
    return True   # no restrictions


def require_auth():
    pass   # no-op


def require_role(*roles: str):
    pass   # no-op


def is_authenticated() -> bool:
    return True


def do_logout():
    pass
