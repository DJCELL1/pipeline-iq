"""
Loss Analysis page — why we're losing, who we lose with most, trends.
"""
import datetime
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.auth import require_auth
from utils import api_client as api


@st.cache_data(ttl=120, show_spinner=False)
def _load_all_jobs():
    return api.get_jobs()


@st.cache_data(ttl=120, show_spinner=False)
def _load_qs():
    return api.get_qs_list()


def show():
    require_auth()
    st.title("Loss Analysis")
    st.caption("Understanding why we lose and where to improve")

    # ── Year filter ───────────────────────────────────────────────────────────
    current_year = datetime.date.today().year
    year_options = ["All Time"] + [str(y) for y in range(current_year, current_year - 6, -1)]
    selected_year = st.selectbox("Filter by Year", year_options, index=0,
                                 label_visibility="collapsed", key="loss_year_filter")

    def in_year(date_str):
        if selected_year == "All Time":
            return True
        return (date_str or "").startswith(selected_year)

    st.divider()

    # ── Load data once ────────────────────────────────────────────────────────
    with st.spinner("Loading data…"):
        all_jobs = _load_all_jobs()
        all_qs   = _load_qs()

    # Split into won / lost filtered by year
    WON_STATUSES = {"won", "in_delivery", "invoiced", "complete"}
    lost_jobs = [j for j in all_jobs
                 if j.get("status") == "lost"
                 and in_year((j.get("quote_date") or "")[:4])]
    won_jobs  = [j for j in all_jobs
                 if j.get("status") in WON_STATUSES
                 and in_year((j.get("quote_date") or "")[:4])]

    col1, col2 = st.columns(2)

    # ── Loss Reasons Pie ──────────────────────────────────────────────────────
    with col1:
        st.subheader("Loss Reasons")
        if lost_jobs:
            reason_counts = {}
            for j in lost_jobs:
                r = j.get("loss_reason") or "Not specified"
                reason_counts[r] = reason_counts.get(r, 0) + 1
            df = pd.DataFrame([{"reason": k, "count": v} for k, v in reason_counts.items()])
            fig = px.pie(df, names="reason", values="count",
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(height=340, margin=dict(t=10, b=10, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No lost jobs for selected period.")

    # ── Win vs Loss count by month ────────────────────────────────────────────
    with col2:
        st.subheader("Win vs Loss Trend (Count)")
        month_counts = {}
        for j in all_jobs:
            m = (j.get("quote_date") or "")[:7]
            if not m or not in_year(m[:4]):
                continue
            if m not in month_counts:
                month_counts[m] = {"month": m, "won": 0, "lost": 0}
            if j.get("status") in WON_STATUSES:
                month_counts[m]["won"] += 1
            elif j.get("status") == "lost":
                month_counts[m]["lost"] += 1

        if month_counts:
            df = pd.DataFrame(sorted(month_counts.values(), key=lambda x: x["month"]))
            fig = go.Figure()
            fig.add_scatter(name="Won",  x=df["month"], y=df["won"],  mode="lines+markers",
                            line=dict(color="#2ecc71", width=2))
            fig.add_scatter(name="Lost", x=df["month"], y=df["lost"], mode="lines+markers",
                            line=dict(color="#e74c3c", width=2))
            fig.update_layout(height=340, margin=dict(t=10, b=10, l=0, r=0),
                              yaxis_title="Job Count")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

    # ── Win vs Loss by $ Value ────────────────────────────────────────────────
    st.subheader("Won vs Lost — $ Value by Month")
    month_values = {}
    for j in all_jobs:
        m = (j.get("quote_date") or "")[:7]
        if not m or not in_year(m[:4]):
            continue
        val = j.get("quote_value") or 0
        if m not in month_values:
            month_values[m] = {"month": m, "won_value": 0, "lost_value": 0}
        if j.get("status") in WON_STATUSES:
            month_values[m]["won_value"] += val
        elif j.get("status") == "lost":
            month_values[m]["lost_value"] += val

    if month_values:
        df_val = pd.DataFrame(sorted(month_values.values(), key=lambda x: x["month"]))
        fig = go.Figure()
        fig.add_bar(name="Won ($)",  x=df_val["month"], y=df_val["won_value"],
                    marker_color="#2ecc71", opacity=0.85)
        fig.add_bar(name="Lost ($)", x=df_val["month"], y=df_val["lost_value"],
                    marker_color="#e74c3c", opacity=0.85)
        fig.update_layout(barmode="group", height=340, margin=dict(t=10, b=10, l=0, r=0),
                          yaxis_title="$ Value", yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data yet.")

    st.divider()

    # ── Companies — loss count + value ───────────────────────────────────────
    st.subheader("Companies — Loss Analysis")
    if lost_jobs:
        co_losses = {}
        co_value  = {}
        for j in lost_jobs:
            co = j.get("company_name") or "Unknown"
            co_losses[co] = co_losses.get(co, 0) + 1
            co_value[co]  = co_value.get(co, 0) + (j.get("quote_value") or 0)

        df_co = pd.DataFrame([
            {"Company": k, "Losses": co_losses[k], "Lost Value ($)": co_value[k]}
            for k in co_losses
        ]).sort_values("Losses", ascending=False)

        col3, col4 = st.columns(2)
        with col3:
            st.caption("Losses by Company (count)")
            fig = px.bar(df_co.head(10), x="Losses", y="Company", orientation="h",
                         color_discrete_sequence=["#e74c3c"])
            fig.update_layout(height=300, margin=dict(t=10, b=10, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        with col4:
            st.caption("Value Lost by Company ($)")
            fig = px.bar(df_co.sort_values("Lost Value ($)", ascending=False).head(10),
                         x="Lost Value ($)", y="Company", orientation="h",
                         color_discrete_sequence=["#e67e22"])
            fig.update_layout(height=300, margin=dict(t=10, b=10, l=0, r=0),
                              xaxis_tickprefix="$", xaxis_tickformat=",.0f")
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # ── QS's with no wins ─────────────────────────────────────────────────
        st.subheader("QS's — All-time Loss Record")
        never_won = [q for q in all_qs
                     if q.get("total_jobs", 0) > 0 and q.get("won_jobs", 0) == 0]
        if never_won:
            st.warning(f"**{len(never_won)} QS(s)** with no wins on record:")
            st.dataframe(pd.DataFrame([
                {"Name": q["name"], "Company": q.get("company_name") or "—",
                 "Total Jobs": q["total_jobs"]} for q in never_won
            ]), use_container_width=True, hide_index=True)
        else:
            st.success("All QS's have at least one win on record.")

        st.divider()

        # ── Full lost jobs table ──────────────────────────────────────────────
        st.subheader(f"All Lost Jobs ({len(lost_jobs)})")
        st.dataframe(pd.DataFrame([{
            "Job #":    j["job_number"],
            "Job Name": j["job_name"],
            "Company":  j.get("company_name") or "—",
            "QS":       j.get("qs_name") or "—",
            "Value":    f"${j['quote_value']:,.0f}" if j.get("quote_value") else "—",
            "Date":     (j.get("quote_date") or "")[:10] or "—",
            "Reason":   j.get("loss_reason") or "Not specified",
        } for j in lost_jobs]), use_container_width=True, height=350, hide_index=True)
    else:
        st.info("No lost jobs on record yet.")
