"""
Pipeline IQ — Streamlit entry point.
Handles session-state routing, sidebar navigation, and auth gating.
"""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Pipeline IQ",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.auth import is_authenticated, login_page, get_user, get_role, do_logout

# ── Auth gate ──────────────────────────────────────────────────────────────────
if not is_authenticated():
    login_page()
    st.stop()

# ── Import pages (only after auth is confirmed) ────────────────────────────────
from pages import (
    home, overview, companies, company_detail, qs_intelligence,
    qs_leaderboard, loss_analysis, job_log, upload, admin,
)

# ── Navigation definition ──────────────────────────────────────────────────────
PAGES = {
    "home":           ("🏠 My Actions",         home),
    "overview":       ("📊 Overview",           overview),
    "companies":      ("🏢 Companies",          companies),
    "company_detail": (None,                     company_detail),   # hidden nav item
    "qs_intelligence":("👤 QS Intelligence",    qs_intelligence),
    "qs_leaderboard": ("🏆 QS Leaderboard",     qs_leaderboard),
    "loss_analysis":  ("📉 Loss Analysis",      loss_analysis),
    "job_log":        ("📋 Job Log",             job_log),
    "upload":         ("⬆️ Upload Jobs",         upload),
    "admin":          ("⚙️ Admin",               admin),
}

# Pages visible in the sidebar
NAV_PAGES = [
    "home", "overview", "companies", "qs_intelligence",
    "qs_leaderboard", "loss_analysis", "job_log", "upload",
]

user = get_user()
role = get_role()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style='text-align:center;padding:0.5rem 0 1rem'>
            <span style='font-size:2rem'>🏗️</span><br>
            <strong style='font-size:1.1rem'>Pipeline IQ</strong><br>
            <span style='color:#888;font-size:0.8rem'>Hardware Direct</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    current = st.session_state.get("page", "home")

    for page_key in NAV_PAGES:
        label, _ = PAGES[page_key]
        is_active = current == page_key

        if st.button(
            label,
            key=f"nav_{page_key}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            # Clear detail selections when navigating away
            if page_key != "company_detail":
                st.session_state.pop("selected_company_id", None)
            if page_key not in ("qs_intelligence",):
                st.session_state.pop("selected_qs_id", None)
            if page_key not in ("job_log",):
                st.session_state.pop("selected_job_id", None)
            st.session_state["page"] = page_key
            st.rerun()

    # Admin-only link
    if role == "admin":
        if st.button("⚙️ Admin", key="nav_admin", use_container_width=True,
                     type="primary" if current == "admin" else "secondary"):
            st.session_state["page"] = "admin"
            st.rerun()

    st.divider()
    st.caption(f"👤 **{user.get('name')}**")
    st.caption(f"🔑 {role.replace('_', ' ').title()}")
    if st.button("Sign Out", use_container_width=True):
        do_logout()
        st.rerun()

# ── Route to current page ──────────────────────────────────────────────────────
page_key = st.session_state.get("page", "home")

# Fallback unknown page → home
if page_key not in PAGES:
    page_key = "home"
    st.session_state["page"] = "home"

_, page_module = PAGES[page_key]
page_module.show()
