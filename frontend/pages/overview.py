"""
Overview Dashboard — pipeline metrics and Plotly charts.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from utils.auth import require_auth
from utils.data import get_all_jobs, get_all_companies, get_all_qs, get_dashboard_stats, in_year, WON_STATUSES


def show():
    require_auth()
    year = st.session_state.get("selected_year", "All Time")
    st.title("Overview Dashboard")
    if year != "All Time":
        st.caption(f"Filtered to **{year}**")

    with st.spinner("Loading…"):
        all_jobs   = get_all_jobs()
        companies  = get_all_companies()
        all_qs     = get_all_qs()

    # Apply year filter
    jobs = [j for j in all_jobs if in_year((j.get("quote_date") or "")[:4])]
    won_jobs  = [j for j in jobs if j.get("status") in WON_STATUSES]
    lost_jobs = [j for j in jobs if j.get("status") == "lost"]

    total_value   = sum(j.get("quote_value") or 0 for j in jobs)
    win_rate      = len(won_jobs) / len(jobs) if jobs else 0
    pipeline_jobs = [j for j in jobs if j.get("status") in ("at_quote", "pursuing")]

    # ── KPI cards ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Pipeline Value",  f"${total_value:,.0f}")
    c2.metric("Win Rate",        f"{win_rate*100:.1f}%")
    c3.metric("Total Jobs",      len(jobs))
    c4.metric("Active Quotes",   len(pipeline_jobs))
    c5.metric("Companies",       len(companies))
    c6.metric("QS's",            len(all_qs))

    st.divider()

    col_left, col_right = st.columns(2)

    # ── Win/Loss by Month ─────────────────────────────────────────────────────
    with col_left:
        st.subheader("Win / Loss by Month")
        month_counts = {}
        for j in jobs:
            m = (j.get("quote_date") or "")[:7]
            if not m:
                continue
            if m not in month_counts:
                month_counts[m] = {"month": m, "won": 0, "lost": 0, "other": 0}
            if j.get("status") in WON_STATUSES:
                month_counts[m]["won"] += 1
            elif j.get("status") == "lost":
                month_counts[m]["lost"] += 1
            else:
                month_counts[m]["other"] += 1

        if month_counts:
            df = pd.DataFrame(sorted(month_counts.values(), key=lambda x: x["month"]))
            fig = go.Figure()
            fig.add_bar(name="Won",   x=df["month"], y=df["won"],   marker_color="#2ecc71")
            fig.add_bar(name="Lost",  x=df["month"], y=df["lost"],  marker_color="#e74c3c")
            fig.add_bar(name="Other", x=df["month"], y=df["other"], marker_color="#95a5a6")
            fig.update_layout(barmode="group", height=300, margin=dict(t=10, b=10, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

    # ── Top Companies by Value ─────────────────────────────────────────────────
    with col_right:
        st.subheader("Top Companies by Quote Value")
        co_values = {}
        for j in jobs:
            co = j.get("company_name") or "Unknown"
            co_values[co] = co_values.get(co, 0) + (j.get("quote_value") or 0)

        if co_values:
            df_co = pd.DataFrame([{"company": k, "total_value": v}
                                   for k, v in co_values.items()]
                                  ).sort_values("total_value", ascending=False).head(10)
            fig = px.bar(df_co, x="total_value", y="company", orientation="h",
                         labels={"total_value": "Total Value ($)", "company": ""},
                         color_discrete_sequence=["#3498db"])
            fig.update_layout(height=300, margin=dict(t=10, b=10, l=0, r=0),
                               xaxis_tickprefix="$", xaxis_tickformat=",.0f")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

    st.divider()

    col_left2, col_right2 = st.columns(2)

    # ── $ Value Won vs Lost by month ──────────────────────────────────────────
    with col_left2:
        st.subheader("Won vs Lost — $ Value")
        month_values = {}
        for j in jobs:
            m = (j.get("quote_date") or "")[:7]
            if not m:
                continue
            val = j.get("quote_value") or 0
            if m not in month_values:
                month_values[m] = {"month": m, "won_value": 0, "lost_value": 0}
            if j.get("status") in WON_STATUSES:
                month_values[m]["won_value"] += val
            elif j.get("status") == "lost":
                month_values[m]["lost_value"] += val

        if month_values:
            df_v = pd.DataFrame(sorted(month_values.values(), key=lambda x: x["month"]))
            fig = go.Figure()
            fig.add_bar(name="Won ($)",  x=df_v["month"], y=df_v["won_value"],  marker_color="#2ecc71", opacity=0.85)
            fig.add_bar(name="Lost ($)", x=df_v["month"], y=df_v["lost_value"], marker_color="#e74c3c", opacity=0.85)
            fig.update_layout(barmode="group", height=280, margin=dict(t=10, b=10, l=0, r=0),
                              yaxis_tickprefix="$", yaxis_tickformat=",.0f")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

    # ── Recent Jobs ────────────────────────────────────────────────────────────
    with col_right2:
        st.subheader("Recent Jobs")
        STATUS_ICON = {
            "at_quote": "📝", "pursuing": "🎯", "won": "✅",
            "lost": "❌", "in_delivery": "🔨", "invoiced": "💰", "complete": "🏁",
        }
        recent = sorted(jobs, key=lambda j: j.get("quote_date") or "", reverse=True)[:8]
        if recent:
            for j in recent:
                icon = STATUS_ICON.get(j["status"], "•")
                val  = f"${j['quote_value']:,.0f}" if j.get("quote_value") else "—"
                st.markdown(
                    f"{icon} **{j['job_number']}** {j['job_name'][:40]}  "
                    f"`{j['status'].replace('_', ' ').title()}` — {val}"
                )
        else:
            st.info("No jobs yet.")
