"""
Cached data fetchers — all pages import from here instead of calling api directly.
Cache TTL = 2 minutes so the app stays responsive without hammering the backend.
"""
import streamlit as st
from utils import api_client as api


@st.cache_data(ttl=120, show_spinner=False)
def get_all_jobs():
    return api.get_jobs()


@st.cache_data(ttl=120, show_spinner=False)
def get_all_companies():
    return api.get_companies()


@st.cache_data(ttl=120, show_spinner=False)
def get_all_qs():
    return api.get_qs_list()


@st.cache_data(ttl=120, show_spinner=False)
def get_dashboard_stats():
    return api.get_dashboard_stats()


def get_selected_year() -> str:
    """Return the globally selected year from session state."""
    return st.session_state.get("selected_year", "All Time")


def in_year(date_str: str) -> bool:
    """Return True if date_str (YYYY-...) matches the global year filter."""
    year = get_selected_year()
    if year == "All Time":
        return True
    return (date_str or "").startswith(year)


WON_STATUSES = {"won", "in_delivery", "invoiced", "complete"}
