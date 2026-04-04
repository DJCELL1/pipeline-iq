"""
QS Leaderboard — ranked table filterable by company, flag, win rate.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.auth import require_auth
from utils import api_client as api
from utils.data import get_all_companies, get_all_qs

FLAG_LABELS = {
    "loyal":        "🟢 Loyal",
    "loss_streak":  "🔴 Loss Streak",
    "payment_risk": "🟠 Payment Risk",
    "gone_cold":    "🔵 Gone Cold",
}


def show():
    require_auth()
    st.title("QS Leaderboard")
    st.caption("Quantity Surveyors ranked by overall intelligence score")

    with st.spinner("Loading…"):
        all_qs    = get_all_qs()
        companies = get_all_companies()

    col1, col2, col3 = st.columns(3)

    with col1:
        co_map = {"All Companies": None}
        co_map.update({c["name"]: c["id"] for c in companies})
        selected_co = st.selectbox("Filter by Company", list(co_map.keys()))

    with col2:
        flag_options = ["All Flags", "loyal", "loss_streak", "payment_risk", "gone_cold"]
        selected_flag = st.selectbox("Filter by Flag", flag_options,
                                     format_func=lambda f: FLAG_LABELS.get(f, f.replace("_", " ").title()))

    with col3:
        min_wr = st.slider("Min Win Rate (%)", 0, 100, 0, step=5)

    # Filter client-side from cached data
    leaderboard = all_qs
    if co_map.get(selected_co):
        leaderboard = [q for q in leaderboard if q.get("company_id") == co_map[selected_co]]
    if selected_flag != "All Flags":
        leaderboard = [q for q in leaderboard if selected_flag in q.get("flags", [])]
    if min_wr > 0:
        leaderboard = [q for q in leaderboard if (q.get("win_rate") or 0) * 100 >= min_wr]

    # Sort by overall score desc
    leaderboard = sorted(leaderboard, key=lambda q: (q.get("scores") or {}).get("overall_score") or 0, reverse=True)

    if not leaderboard:
        st.info("No QS's match the current filters.")
        return

    rows = []
    for rank, q in enumerate(leaderboard, 1):
        scores = q.get("scores", {})
        flags  = q.get("flags", [])
        wr     = q.get("win_rate")
        rows.append({
            "Rank":           rank,
            "_id":            q["id"],
            "Name":           q["name"],
            "Company":        q.get("company_name") or "—",
            "Total Jobs":     q.get("total_jobs", 0),
            "Win Rate":       f"{wr*100:.0f}%" if wr is not None else "—",
            "Overall (/10)":  round(scores.get("overall_score") or 0, 1),
            "Win Likelihood": round(scores.get("win_likelihood") or 0, 1),
            "Relationship":   round(scores.get("relationship_quality") or 0, 1),
            "Delivery":       round(scores.get("delivery_experience") or 0, 1),
            "Payment":        round(scores.get("payment_reliability") or 0, 1),
            "Flags":          " ".join(FLAG_LABELS.get(f, f) for f in flags) or "—",
        })

    st.caption(f"{len(rows)} QS's")
    st.dataframe(pd.DataFrame(rows).drop(columns=["_id"]), use_container_width=True, height=480, hide_index=True)

    st.divider()
    st.subheader("Score Comparison Chart")
    chart_data = [{"name": r["Name"], "score": r["Overall (/10)"]} for r in rows[:15]]
    if chart_data:
        cdf = pd.DataFrame(chart_data)
        fig = px.bar(cdf, x="score", y="name", orientation="h",
                     labels={"score": "Overall Score (/10)", "name": ""},
                     color="score", color_continuous_scale="RdYlGn", range_color=[0, 10])
        fig.update_layout(height=max(300, len(chart_data) * 28), margin=dict(t=10, b=10, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    selected_name = st.selectbox("Open QS Detail", [r["Name"] for r in rows])
    if st.button("View QS →"):
        selected = next(q for q in leaderboard if q["name"] == selected_name)
        st.session_state["selected_qs_id"] = selected["id"]
        st.session_state["page"] = "qs_intelligence"
        st.rerun()
