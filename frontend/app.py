"""
Pipeline IQ — Streamlit entry point.
No login required. All pages accessible. Default role: admin.
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

# ── Set default session user (no login required) ───────────────────────────────
if "user" not in st.session_state:
    st.session_state["user"] = {
        "id": 1,
        "name": "Hardware Direct",
        "email": "admin@hardwaredirect.com.au",
        "role": "admin",
    }

# ── Import pages ───────────────────────────────────────────────────────────────
from pages import (
    home, overview, companies, company_detail, qs_intelligence,
    qs_leaderboard, loss_analysis, job_log, upload, admin,
)

# ── Navigation definition ──────────────────────────────────────────────────────
PAGES = {
    "home":            ("🏠 My Actions",       home),
    "overview":        ("📊 Overview",          overview),
    "companies":       ("🏢 Companies",         companies),
    "company_detail":  (None,                    company_detail),   # hidden
    "qs_intelligence": ("👤 QS Intelligence",   qs_intelligence),
    "qs_leaderboard":  ("🏆 QS Leaderboard",    qs_leaderboard),
    "loss_analysis":   ("📉 Loss Analysis",     loss_analysis),
    "job_log":         ("📋 Job Log",            job_log),
    "upload":          ("⬆️ Upload Jobs",        upload),
    "admin":           ("⚙️ Admin",              admin),
}

NAV_PAGES = [
    "home", "overview", "companies", "qs_intelligence",
    "qs_leaderboard", "loss_analysis", "job_log", "upload", "admin",
]

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
            if page_key != "company_detail":
                st.session_state.pop("selected_company_id", None)
            if page_key not in ("qs_intelligence",):
                st.session_state.pop("selected_qs_id", None)
            if page_key not in ("job_log",):
                st.session_state.pop("selected_job_id", None)
            st.session_state["page"] = page_key
            st.rerun()

    st.divider()

    # ── Global year filter ─────────────────────────────────────────────────
    import datetime
    current_year = datetime.date.today().year
    year_options = ["All Time"] + [str(y) for y in range(current_year, current_year - 6, -1)]
    selected_year = st.selectbox(
        "📅 Year",
        year_options,
        index=year_options.index(st.session_state.get("selected_year", "All Time")),
        key="year_filter_widget",
    )
    if selected_year != st.session_state.get("selected_year"):
        st.session_state["selected_year"] = selected_year
        st.rerun()

# ── Route to current page ──────────────────────────────────────────────────────
page_key = st.session_state.get("page", "home")
if page_key not in PAGES:
    page_key = "home"
    st.session_state["page"] = "home"

_, page_module = PAGES[page_key]
page_module.show()
