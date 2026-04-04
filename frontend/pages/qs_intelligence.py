"""
QS Intelligence page — searchable QS list + QS detail view.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.auth import require_auth, get_user
from utils import api_client as api
from utils.data import get_all_companies, get_all_qs

FLAG_INFO = {
    "loyal":        ("🟢", "Loyal",        "#2ecc71"),
    "loss_streak":  ("🔴", "Loss Streak",  "#e74c3c"),
    "payment_risk": ("🟠", "Payment Risk", "#f39c12"),
    "gone_cold":    ("🔵", "Gone Cold",    "#3498db"),
}

STATUS_ICON = {
    "at_quote": "📝", "pursuing": "🎯", "won": "✅",
    "lost": "❌", "in_delivery": "🔨", "invoiced": "💰", "complete": "🏁",
}


def gauge(title, value, max_val=10):
    if value is None:
        fig = go.Figure(go.Indicator(
            mode="gauge", value=0,
            title={"text": f"{title}<br><span style='font-size:0.7em;color:grey'>No data</span>"},
            gauge={"axis": {"range": [0, max_val]}, "bar": {"color": "#bbb"}},
        ))
    else:
        colour = "#2ecc71" if value >= 7 else "#f39c12" if value >= 4 else "#e74c3c"
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=value,
            number={"suffix": f"/{max_val}"},
            title={"text": title},
            gauge={"axis": {"range": [0, max_val]}, "bar": {"color": colour},
                   "steps": [{"range": [0, 4], "color": "#fdecea"},
                              {"range": [4, 7], "color": "#fef9e7"},
                              {"range": [7, 10], "color": "#eafaf1"}]},
        ))
    fig.update_layout(height=220, margin=dict(t=30, b=10, l=10, r=10))
    return fig


def show_qs_detail(qs_id: int):
    qs = api.get_qs(qs_id)
    if not qs:
        st.error("QS not found.")
        return

    if st.button("← QS Intelligence"):
        st.session_state.pop("selected_qs_id", None)
        st.rerun()

    st.title(qs["name"])
    if qs.get("company_name"):
        st.caption(f"Company: **{qs['company_name']}**")
    if qs.get("email"):
        st.caption(f"📧 {qs['email']}")
    if qs.get("phone"):
        st.caption(f"📞 {qs['phone']}")

    flags = qs.get("flags", [])
    if flags:
        badge_html = " ".join(
            f"<span style='background:{FLAG_INFO.get(f,('','','#aaa'))[2]};color:white;"
            f"padding:3px 10px;border-radius:12px;font-size:0.8em;margin-right:4px'>"
            f"{FLAG_INFO.get(f,('','',''))[0]} {FLAG_INFO.get(f,('',f,''))[1]}</span>"
            for f in flags
        )
        st.markdown(badge_html, unsafe_allow_html=True)
        st.write("")

    total = qs.get("total_jobs", 0)
    won   = qs.get("won_jobs", 0)
    wr    = qs.get("win_rate")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Jobs", total)
    c2.metric("Won Jobs",   won)
    c3.metric("Win Rate",   f"{wr*100:.0f}%" if wr is not None else "—")

    scores = qs.get("scores", {})
    st.subheader("Intelligence Scores")
    g1, g2, g3, g4, g5 = st.columns(5)
    with g1: st.plotly_chart(gauge("Win Likelihood",    scores.get("win_likelihood")),       use_container_width=True)
    with g2: st.plotly_chart(gauge("Relationship",      scores.get("relationship_quality")), use_container_width=True)
    with g3: st.plotly_chart(gauge("Delivery",          scores.get("delivery_experience")),  use_container_width=True)
    with g4: st.plotly_chart(gauge("Payment",           scores.get("payment_reliability")),  use_container_width=True)
    with g5: st.plotly_chart(gauge("Overall",           scores.get("overall_score")),        use_container_width=True)

    st.divider()
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Job History")
        jobs = qs.get("jobs", [])
        if jobs:
            for j in jobs:
                icon = STATUS_ICON.get(j["status"], "•")
                val  = f"${j['quote_value']:,.0f}" if j.get("quote_value") else "—"
                st.markdown(f"{icon} **{j['job_number']}** {j['job_name'][:45]}  |  {val}  |  {j.get('company_name') or '—'}")
        else:
            st.info("No jobs on record.")

    with col_right:
        st.subheader("Comments & Notes")
        comments = api.get_comments("qs", qs_id)
        for c in comments:
            st.markdown(
                f"**{c['user_name']}**  "
                f"<span style='color:#888;font-size:0.8em'>{c['created_at'][:10]}</span>",
                unsafe_allow_html=True,
            )
            st.write(c["body"])
            st.divider()

        with st.form("new_comment_qs"):
            new_body = st.text_area("Add a comment", height=80, label_visibility="collapsed",
                                    placeholder="Leave a note…")
            if st.form_submit_button("Post Comment"):
                if new_body.strip():
                    api.add_comment("qs", qs_id, new_body.strip())
                    st.rerun()


def show():
    require_auth()

    selected_qs_id = st.session_state.get("selected_qs_id")
    if selected_qs_id:
        show_qs_detail(selected_qs_id)
        return

    st.title("QS Intelligence")

    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("Search QS", placeholder="Name…", label_visibility="collapsed")
    with col2:
        add_btn = st.button("+ Add QS", use_container_width=True)

    if add_btn:
        st.session_state["show_add_qs"] = True

    if st.session_state.get("show_add_qs"):
        with st.spinner("Loading companies…"):
            companies = get_all_companies()
        co_options = {c["name"]: c["id"] for c in companies}
        with st.form("add_qs_form"):
            st.subheader("New Quantity Surveyor")
            qs_name    = st.text_input("Name")
            qs_email   = st.text_input("Email")
            qs_phone   = st.text_input("Phone")
            qs_company = st.selectbox("Company", ["(None)"] + list(co_options.keys()))
            ok = st.form_submit_button("Create")
        if ok and qs_name:
            api.create_qs({
                "name": qs_name,
                "email": qs_email or None,
                "phone": qs_phone or None,
                "company_id": co_options.get(qs_company) if qs_company != "(None)" else None,
            })
            st.cache_data.clear()
            st.session_state.pop("show_add_qs", None)
            st.rerun()

    with st.spinner("Loading…"):
        all_qs = get_all_qs()

    filtered = [q for q in all_qs if not search or search.lower() in q["name"].lower()]

    if not filtered:
        st.info("No QS's found.")
        return

    rows = []
    for q in filtered:
        scores = q.get("scores", {})
        flags  = q.get("flags", [])
        wr     = q.get("win_rate")
        rows.append({
            "_id":             q["id"],
            "Name":            q["name"],
            "Company":         q.get("company_name") or "—",
            "Win Rate":        f"{wr*100:.0f}%" if wr is not None else "—",
            "Total Jobs":      q.get("total_jobs", 0),
            "Overall":         round(scores.get("overall_score") or 0, 1),
            "Win Likelihood":  round(scores.get("win_likelihood") or 0, 1),
            "Relationship":    round(scores.get("relationship_quality") or 0, 1),
            "Flags":           " ".join(FLAG_INFO.get(f, ("", f, ""))[1] for f in flags) or "—",
        })

    st.caption(f"{len(filtered)} QS's")
    st.dataframe(pd.DataFrame(rows).drop(columns=["_id"]), use_container_width=True, height=400, hide_index=True)

    st.divider()
    qs_names = [q["name"] for q in filtered]
    selected_name = st.selectbox("Select QS", qs_names, label_visibility="collapsed")
    if st.button("Open QS Detail →"):
        selected = next(q for q in filtered if q["name"] == selected_name)
        st.session_state["selected_qs_id"] = selected["id"]
        st.rerun()
