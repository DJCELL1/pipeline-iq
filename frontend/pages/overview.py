"""
Overview Dashboard — pipeline metrics and Plotly charts.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from utils.auth import require_auth
from utils import api_client as api


def show():
    require_auth()
    st.title("Overview Dashboard")

    stats = api.get_dashboard_stats()
    if not stats:
        st.error("Could not load dashboard stats.")
        return

    # ── KPI cards ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Pipeline Value",  f"${stats['total_pipeline_value']:,.0f}")
    c2.metric("Win Rate",        f"{stats['win_rate']*100:.1f}%")
    c3.metric("Jobs This Month", stats['jobs_this_month'])
    c4.metric("Active Jobs",     stats['active_jobs'])
    c5.metric("Companies",       stats['total_companies'])
    c6.metric("QS's",            stats['total_qs'])

    st.divider()

    col_left, col_right = st.columns(2)

    # ── Win/Loss by Month ─────────────────────────────────────────────────────
    with col_left:
        st.subheader("Win / Loss by Month")
        wl_data = api.get_win_loss_by_month()
        if wl_data:
            df = pd.DataFrame(wl_data)
            fig = go.Figure()
            fig.add_bar(name="Won",  x=df["month"], y=df["won"],  marker_color="#2ecc71")
            fig.add_bar(name="Lost", x=df["month"], y=df["lost"], marker_color="#e74c3c")
            fig.add_bar(name="Other",x=df["month"], y=df.get("other", 0), marker_color="#95a5a6")
            fig.update_layout(barmode="group", height=300, margin=dict(t=10, b=10, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

    # ── Top Companies by Value ─────────────────────────────────────────────────
    with col_right:
        st.subheader("Top Companies by Quote Value")
        top_co = api.get_top_companies_by_value()
        if top_co:
            df = pd.DataFrame(top_co)
            fig = px.bar(df, x="total_value", y="company", orientation="h",
                         labels={"total_value": "Total Value ($)", "company": ""},
                         color_discrete_sequence=["#3498db"])
            fig.update_layout(height=300, margin=dict(t=10, b=10, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

    st.divider()

    col_left2, col_right2 = st.columns(2)

    # ── Companies score distribution ──────────────────────────────────────────
    with col_left2:
        st.subheader("Company Score Distribution")
        companies = api.get_companies()
        if companies:
            scores = [c.get("scores", {}).get("overall_score") for c in companies if c.get("scores", {}).get("overall_score") is not None]
            if scores:
                fig = px.histogram(x=scores, nbins=10, range_x=[0, 10],
                                   labels={"x": "Overall Score", "count": "Companies"},
                                   color_discrete_sequence=["#9b59b6"])
                fig.update_layout(height=280, margin=dict(t=10, b=10, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No scores calculated yet.")
        else:
            st.info("No companies.")

    # ── Recent Activity ────────────────────────────────────────────────────────
    with col_right2:
        st.subheader("Recent Jobs")
        jobs = api.get_jobs()
        if jobs:
            recent = jobs[:8]
            STATUS_ICON = {
                "at_quote": "📝", "pursuing": "🎯", "won": "✅",
                "lost": "❌", "in_delivery": "🔨", "invoiced": "💰", "complete": "🏁",
            }
            for j in recent:
                icon = STATUS_ICON.get(j["status"], "•")
                val = f"${j['quote_value']:,.0f}" if j.get("quote_value") else "—"
                st.markdown(
                    f"{icon} **{j['job_number']}** {j['job_name'][:40]}  "
                    f"`{j['status'].replace('_', ' ').title()}` — {val}"
                )
        else:
            st.info("No jobs yet.")
