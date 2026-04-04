"""
Loss Analysis page — why we're losing, who we lose with most, trends.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.auth import require_auth
from utils import api_client as api


def show():
    require_auth()
    st.title("Loss Analysis")
    st.caption("Understanding why we lose and where to improve")

    # ── Year filter ───────────────────────────────────────────────────────────
    import datetime
    current_year = datetime.date.today().year
    available_years = list(range(current_year, current_year - 6, -1))  # last 6 years
    year_options = ["All Time"] + [str(y) for y in available_years]

    selected_year = st.selectbox("Filter by Year", year_options, index=0, label_visibility="collapsed",
                                  key="loss_year_filter")

    def in_year(date_str):
        if selected_year == "All Time":
            return True
        return (date_str or "").startswith(selected_year)

    st.divider()

    col1, col2 = st.columns(2)

    # ── Loss Reasons Breakdown ────────────────────────────────────────────────
    with col1:
        st.subheader("Loss Reasons")
        reasons = api.get_loss_reasons()
        if reasons:
            # filter by year client-side
            all_lost = api.get_jobs(status="lost")
            filtered_lost = [j for j in all_lost if in_year((j.get("quote_date") or "")[:4])]
            reason_counts = {}
            for j in filtered_lost:
                r = j.get("loss_reason") or "Not specified"
                reason_counts[r] = reason_counts.get(r, 0) + 1
            if reason_counts:
                df = pd.DataFrame([{"reason": k, "count": v} for k, v in reason_counts.items()])
                fig = px.pie(df, names="reason", values="count",
                             color_discrete_sequence=px.colors.qualitative.Set3)
                fig.update_layout(height=340, margin=dict(t=10, b=10, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No lost jobs for selected year.")
        else:
            st.info("No lost jobs yet.")

    # ── Win/Loss by Month ─────────────────────────────────────────────────────
    with col2:
        st.subheader("Win vs Loss Trend (Count)")
        wl_data = api.get_win_loss_by_month()
        if wl_data:
            df = pd.DataFrame(wl_data)
            if selected_year != "All Time":
                df = df[df["month"].str.startswith(selected_year)]
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

    # ── Win vs Loss by $ Value over time ─────────────────────────────────────
    st.subheader("Won vs Lost — $ Value by Month")
    all_jobs_combined = api.get_jobs()
    if all_jobs_combined:
        value_by_month = {}
        for j in all_jobs_combined:
            date_str = (j.get("quote_date") or "")[:7]  # YYYY-MM
            if not date_str or not in_year(date_str[:4]):
                continue
            val = j.get("quote_value") or 0
            status = j.get("status", "")
            if date_str not in value_by_month:
                value_by_month[date_str] = {"month": date_str, "won_value": 0, "lost_value": 0}
            if status in ("won", "in_delivery", "invoiced", "complete"):
                value_by_month[date_str]["won_value"] += val
            elif status == "lost":
                value_by_month[date_str]["lost_value"] += val

        df_val = pd.DataFrame(sorted(value_by_month.values(), key=lambda x: x["month"]))
        if not df_val.empty:
            fig = go.Figure()
            fig.add_bar(name="Won ($)", x=df_val["month"], y=df_val["won_value"],
                        marker_color="#2ecc71", opacity=0.85)
            fig.add_bar(name="Lost ($)", x=df_val["month"], y=df_val["lost_value"],
                        marker_color="#e74c3c", opacity=0.85)
            fig.update_layout(
                barmode="group", height=340,
                margin=dict(t=10, b=10, l=0, r=0),
                yaxis_title="$ Value",
                yaxis_tickprefix="$",
                yaxis_tickformat=",.0f",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data yet.")

    st.divider()

    # ── Companies we lose most with ───────────────────────────────────────────
    st.subheader("Companies — Loss Analysis")
    all_jobs = [j for j in api.get_jobs(status="lost")
                if in_year((j.get("quote_date") or "")[:4])]
    if all_jobs:
        company_losses = {}
        company_loss_value = {}
        for j in all_jobs:
            co = j.get("company_name") or "Unknown"
            company_losses[co]     = company_losses.get(co, 0) + 1
            company_loss_value[co] = company_loss_value.get(co, 0) + (j.get("quote_value") or 0)

        df_co = pd.DataFrame([
            {"Company": k, "Losses": company_losses[k], "Lost Value ($)": company_loss_value[k]}
            for k in company_losses
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
            fig = px.bar(df_co.head(10), x="Lost Value ($)", y="Company", orientation="h",
                         color_discrete_sequence=["#e67e22"])
            fig.update_layout(height=300, margin=dict(t=10, b=10, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # ── QS's we never win from ────────────────────────────────────────────
        st.subheader("QS's — All-time Loss Record")
        all_qs = api.get_qs_list()
        never_won = [
            q for q in all_qs
            if q.get("total_jobs", 0) > 0 and q.get("won_jobs", 0) == 0
        ]
        if never_won:
            st.warning(f"**{len(never_won)} QS(s)** with no wins on record:")
            rows = [{"Name": q["name"], "Company": q.get("company_name") or "—",
                     "Total Jobs": q["total_jobs"]} for q in never_won]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.success("All QS's have at least one win on record.")

        st.divider()

        # ── Full lost jobs table ───────────────────────────────────────────────
        st.subheader("All Lost Jobs")
        rows = []
        for j in all_jobs:
            rows.append({
                "Job #":    j["job_number"],
                "Job Name": j["job_name"],
                "Company":  j.get("company_name") or "—",
                "QS":       j.get("qs_name") or "—",
                "Value":    f"${j['quote_value']:,.0f}" if j.get("quote_value") else "—",
                "Date":     j.get("quote_date", "")[:10] if j.get("quote_date") else "—",
                "Reason":   j.get("loss_reason") or "Not specified",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, height=350, hide_index=True)
    else:
        st.info("No lost jobs on record yet.")
