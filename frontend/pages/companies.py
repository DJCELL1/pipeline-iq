"""
Companies list page — searchable, filterable, click-through to detail.
"""
import streamlit as st
import pandas as pd
from utils.auth import require_auth
from utils import api_client as api
from utils.data import get_all_companies

FLAG_BADGE = {
    "loyal":        "🟢 Loyal",
    "loss_streak":  "🔴 Loss Streak",
    "payment_risk": "🟠 Payment Risk",
    "gone_cold":    "🔵 Gone Cold",
}


def show():
    require_auth()
    st.title("Companies")

    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        search = st.text_input("Search", placeholder="Company name…", label_visibility="collapsed")
    with col2:
        segment = st.selectbox("Segment", ["All", "Commercial", "Residential", "Industrial", "Other"],
                               label_visibility="collapsed")
    with col3:
        add_btn = st.button("+ Add Company", use_container_width=True)

    if add_btn:
        st.session_state["show_add_company"] = True

    if st.session_state.get("show_add_company"):
        with st.form("add_company_form"):
            st.subheader("New Company")
            c_name = st.text_input("Name")
            c_seg  = st.selectbox("Segment", ["Commercial", "Residential", "Industrial", "Other", ""])
            ok = st.form_submit_button("Create")
        if ok and c_name:
            result = api.create_company(c_name, c_seg)
            if result:
                st.success(f"Created {c_name}")
                st.cache_data.clear()
                st.session_state.pop("show_add_company", None)
                st.rerun()

    with st.spinner("Loading…"):
        companies = get_all_companies()

    # Filter client-side
    seg_filter = "" if segment == "All" else segment
    filtered = [
        c for c in companies
        if (not search or search.lower() in c["name"].lower())
        and (not seg_filter or (c.get("segment") or "") == seg_filter)
    ]

    if not filtered:
        st.info("No companies found.")
        return

    rows = []
    for c in filtered:
        scores = c.get("scores", {})
        flags  = c.get("flags", [])
        rows.append({
            "_id":             c["id"],
            "Company":         c["name"],
            "Segment":         c.get("segment") or "—",
            "Overall Score":   round(scores.get("overall_score") or 0, 1),
            "Win Likelihood":  round(scores.get("win_likelihood") or 0, 1),
            "Relationship":    round(scores.get("relationship_quality") or 0, 1),
            "Delivery":        round(scores.get("delivery_experience") or 0, 1),
            "Payment":         round(scores.get("payment_reliability") or 0, 1),
            "Flags":           " ".join(FLAG_BADGE.get(f, f) for f in flags) or "—",
        })

    df = pd.DataFrame(rows)
    st.caption(f"{len(filtered)} companies")
    st.dataframe(df.drop(columns=["_id"]), use_container_width=True, height=450, hide_index=True)

    st.divider()
    st.subheader("View Company Detail")
    company_names = [c["name"] for c in filtered]
    selected_name = st.selectbox("Select company", company_names, label_visibility="collapsed")
    if st.button("Open Detail →", use_container_width=False):
        selected = next(c for c in filtered if c["name"] == selected_name)
        st.session_state["selected_company_id"] = selected["id"]
        st.session_state["page"] = "company_detail"
        st.rerun()
