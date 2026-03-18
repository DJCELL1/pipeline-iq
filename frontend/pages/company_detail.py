"""
Company Detail page — score gauges, job history, comments thread.
"""
import streamlit as st
import plotly.graph_objects as go
from utils.auth import require_auth, get_user
from utils import api_client as api

FLAG_INFO = {
    "loyal":        ("🟢", "Loyal", "#2ecc71"),
    "loss_streak":  ("🔴", "Loss Streak", "#e74c3c"),
    "payment_risk": ("🟠", "Payment Risk", "#f39c12"),
    "gone_cold":    ("🔵", "Gone Cold", "#3498db"),
}

STATUS_ICON = {
    "at_quote": "📝", "pursuing": "🎯", "won": "✅",
    "lost": "❌", "in_delivery": "🔨", "invoiced": "💰", "complete": "🏁",
}


def gauge(title: str, value, max_val=10):
    if value is None:
        fig = go.Figure(go.Indicator(
            mode="gauge",
            value=0,
            title={"text": f"{title}<br><span style='font-size:0.7em;color:grey'>No data</span>"},
            gauge={"axis": {"range": [0, max_val]}, "bar": {"color": "#bbb"}},
        ))
    else:
        colour = "#2ecc71" if value >= 7 else "#f39c12" if value >= 4 else "#e74c3c"
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": f"/{max_val}"},
            title={"text": title},
            gauge={
                "axis": {"range": [0, max_val]},
                "bar": {"color": colour},
                "steps": [
                    {"range": [0, 4],  "color": "#fdecea"},
                    {"range": [4, 7],  "color": "#fef9e7"},
                    {"range": [7, 10], "color": "#eafaf1"},
                ],
            },
        ))
    fig.update_layout(height=220, margin=dict(t=30, b=10, l=10, r=10))
    return fig


def show():
    require_auth()
    company_id = st.session_state.get("selected_company_id")
    if not company_id:
        st.warning("No company selected.")
        if st.button("← Back to Companies"):
            st.session_state["page"] = "companies"
            st.rerun()
        return

    company = api.get_company(company_id)
    if not company:
        st.error("Company not found.")
        return

    # Header
    st.button("← Companies", on_click=lambda: st.session_state.update(page="companies"))
    st.title(company["name"])
    if company.get("segment"):
        st.caption(f"Segment: **{company['segment']}**")

    # Flags
    flags = company.get("flags", [])
    if flags:
        default_flag = ('', '', '#aaa')
        badge_html = " ".join(
            "<span style='background:{};color:white;"
            "padding:3px 10px;border-radius:12px;font-size:0.8em;margin-right:4px'>"
            "{} {}</span>".format(
                FLAG_INFO.get(f, default_flag)[2],
                FLAG_INFO.get(f, default_flag)[0],
                FLAG_INFO.get(f, ('', f, ''))[1],
            )
            for f in flags
        )
        st.markdown(badge_html, unsafe_allow_html=True)
        st.write("")

    scores = company.get("scores", {})

    # ── Score gauges ──────────────────────────────────────────────────────────
    st.subheader("Intelligence Scores")
    g1, g2, g3, g4, g5 = st.columns(5)
    with g1: st.plotly_chart(gauge("Win Likelihood",    scores.get("win_likelihood")),       use_container_width=True)
    with g2: st.plotly_chart(gauge("Relationship",      scores.get("relationship_quality")), use_container_width=True)
    with g3: st.plotly_chart(gauge("Delivery",          scores.get("delivery_experience")),  use_container_width=True)
    with g4: st.plotly_chart(gauge("Payment",           scores.get("payment_reliability")),  use_container_width=True)
    with g5: st.plotly_chart(gauge("Overall",           scores.get("overall_score")),        use_container_width=True)

    if st.button("🔄 Recalculate Scores"):
        api.recalculate_company(company_id)
        st.rerun()

    st.divider()

    col_left, col_right = st.columns([2, 1])

    # ── Job History ───────────────────────────────────────────────────────────
    with col_left:
        st.subheader("Job History")
        jobs = company.get("jobs", [])
        if jobs:
            for j in jobs:
                icon = STATUS_ICON.get(j["status"], "•")
                val  = f"${j['quote_value']:,.0f}" if j.get("quote_value") else "—"
                qs_n = j.get("qs_name") or "—"
                if st.button(
                    f"{icon} {j['job_number']} — {j['job_name'][:45]}  |  {val}  |  QS: {qs_n}",
                    key=f"job_btn_{j['id']}",
                    use_container_width=True,
                ):
                    st.session_state["selected_job_id"] = j["id"]
                    st.session_state["page"] = "job_log"
                    st.rerun()
        else:
            st.info("No jobs on record.")

        st.divider()

        # ── Linked QS's ───────────────────────────────────────────────────────
        st.subheader("Quantity Surveyors")
        qss = company.get("quantity_surveyors", [])
        if qss:
            for q in qss:
                if st.button(f"👤 {q['name']}  {q.get('email') or ''}", key=f"qs_btn_{q['id']}", use_container_width=False):
                    st.session_state["selected_qs_id"] = q["id"]
                    st.session_state["page"] = "qs_intelligence"
                    st.rerun()
        else:
            st.info("No QS's linked.")

    # ── Comments ──────────────────────────────────────────────────────────────
    with col_right:
        st.subheader("Comments & Notes")
        comments = api.get_comments("company", company_id)
        for c in comments:
            with st.container():
                st.markdown(
                    f"**{c['user_name']}** _{c['role'].replace('_', ' ').title() if c.get('role') else ''}_  "
                    f"<span style='color:#888;font-size:0.8em'>{c['created_at'][:10]}</span>",
                    unsafe_allow_html=True,
                )
                st.write(c["body"])
                st.divider()

        with st.form("new_comment_co"):
            new_body = st.text_area("Add a comment", height=80, label_visibility="collapsed",
                                    placeholder="Leave a note…")
            if st.form_submit_button("Post Comment"):
                if new_body.strip():
                    api.add_comment("company", company_id, new_body.strip())
                    st.rerun()
