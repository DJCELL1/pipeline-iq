"""
Admin page — user management, score weights, flag thresholds.
"""
import streamlit as st
import pandas as pd
from utils.auth import require_auth, require_role
from utils import api_client as api

ROLE_OPTIONS = ["estimator", "sales", "project_manager", "accounts_receivable", "admin"]


def show():
    require_auth()
    require_role("admin")

    st.title("Admin Panel")

    tab_users, tab_weights, tab_flags, tab_system = st.tabs(
        ["👥 Users", "⚖️ Score Weights", "🚩 Flag Thresholds", "🔧 System"]
    )

    # ── Users ─────────────────────────────────────────────────────────────────
    with tab_users:
        st.subheader("User Management")

        users = api.get_users()

        if users:
            rows = [
                {
                    "_id":    u["id"],
                    "Name":   u["name"],
                    "Email":  u["email"],
                    "Role":   u["role"].replace("_", " ").title(),
                    "Active": "✅" if u["is_active"] else "❌",
                }
                for u in users
            ]
            st.dataframe(pd.DataFrame(rows).drop(columns=["_id"]),
                         use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Add New User")
        with st.form("add_user"):
            uc1, uc2 = st.columns(2)
            with uc1:
                u_name  = st.text_input("Name")
                u_email = st.text_input("Email")
            with uc2:
                u_role  = st.selectbox("Role", ROLE_OPTIONS,
                                       format_func=lambda r: r.replace("_", " ").title())
                u_pass  = st.text_input("Password", type="password")
            if st.form_submit_button("Create User"):
                if u_name and u_email and u_pass:
                    result = api.create_user({
                        "name": u_name, "email": u_email,
                        "role": u_role, "password": u_pass,
                    })
                    if result:
                        st.success(f"User '{u_name}' created.")
                        st.rerun()
                else:
                    st.warning("Fill in all fields.")

        st.divider()
        st.subheader("Edit / Deactivate User")
        if users:
            user_map = {f"{u['name']} ({u['email']})": u for u in users}
            sel_user_label = st.selectbox("Select user", list(user_map.keys()))
            sel_user = user_map[sel_user_label]

            with st.form("edit_user"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    new_name   = st.text_input("Name",     value=sel_user["name"])
                    new_email  = st.text_input("Email",    value=sel_user["email"])
                    new_active = st.checkbox("Active",     value=sel_user["is_active"])
                with ec2:
                    cur_role = sel_user["role"]
                    new_role = st.selectbox("Role", ROLE_OPTIONS,
                                            index=ROLE_OPTIONS.index(cur_role) if cur_role in ROLE_OPTIONS else 0,
                                            format_func=lambda r: r.replace("_", " ").title())
                    new_pass = st.text_input("New Password (leave blank to keep)", type="password")

                if st.form_submit_button("Save Changes"):
                    data = {"name": new_name, "email": new_email,
                            "role": new_role, "is_active": new_active}
                    if new_pass:
                        data["password"] = new_pass
                    result = api.update_user(sel_user["id"], data)
                    if result:
                        st.success("User updated.")
                        st.rerun()

            if st.button("🗑️ Delete User", type="secondary"):
                if api.delete_user(sel_user["id"]):
                    st.success("User deleted.")
                    st.rerun()

    # ── Score Weights ──────────────────────────────────────────────────────────
    with tab_weights:
        st.subheader("Score Dimension Weights")
        st.caption("These weights control how the four dimensions are combined into the overall score. They should sum to 1.0.")

        weights = api.get_score_weights()

        with st.form("weights_form"):
            wc1, wc2 = st.columns(2)
            with wc1:
                w_wl = st.slider("Win Likelihood",       0.0, 1.0,
                                 float(weights.get("win_likelihood", 0.25)),      step=0.05)
                w_rq = st.slider("Relationship Quality", 0.0, 1.0,
                                 float(weights.get("relationship_quality", 0.30)), step=0.05)
            with wc2:
                w_de = st.slider("Delivery Experience",  0.0, 1.0,
                                 float(weights.get("delivery_experience", 0.25)), step=0.05)
                w_pr = st.slider("Payment Reliability",  0.0, 1.0,
                                 float(weights.get("payment_reliability", 0.20)), step=0.05)

            total = round(w_wl + w_rq + w_de + w_pr, 2)
            if abs(total - 1.0) > 0.01:
                st.warning(f"Weights sum to {total:.2f} — should be 1.0")
            else:
                st.success(f"Weights sum to {total:.2f} ✓")

            if st.form_submit_button("Save Weights"):
                result = api.update_score_weights({
                    "win_likelihood":      w_wl,
                    "relationship_quality": w_rq,
                    "delivery_experience": w_de,
                    "payment_reliability": w_pr,
                })
                if result:
                    st.success("Weights saved.")

    # ── Flag Thresholds ────────────────────────────────────────────────────────
    with tab_flags:
        st.subheader("Flag Thresholds")
        config = api.get_flag_config()

        with st.form("flag_form"):
            f1, f2 = st.columns(2)
            with f1:
                f_pay  = st.slider("Payment Risk threshold (score below triggers flag)", 0.0, 10.0,
                                   float(config.get("payment_risk_threshold", 4.0)), step=0.5)
                f_cold = st.slider("Gone Cold (months of inactivity)", 1.0, 24.0,
                                   float(config.get("cold_months", 6.0)), step=1.0)
            with f2:
                f_streak = st.slider("Loss Streak count (consecutive losses)", 2.0, 10.0,
                                     float(config.get("loss_streak_count", 3.0)), step=1.0)
                f_loyal  = st.slider("Loyal win rate threshold (0–1)", 0.0, 1.0,
                                     float(config.get("loyal_win_rate", 0.6)), step=0.05)

            if st.form_submit_button("Save Flag Config"):
                result = api.update_flag_config({
                    "payment_risk_threshold": f_pay,
                    "cold_months":            f_cold,
                    "loss_streak_count":      f_streak,
                    "loyal_win_rate":         f_loyal,
                })
                if result:
                    st.success("Flag config saved.")

    # ── System ────────────────────────────────────────────────────────────────
    with tab_system:
        st.subheader("System Actions")

        st.markdown("**Recalculate all scores** — triggers scoring engine for every company and QS in the database.")
        if st.button("🔄 Recalculate All Scores", type="primary"):
            with st.spinner("Recalculating…"):
                result = api.recalculate_all()
            if result:
                st.success(
                    f"Done! Recalculated {result.get('recalculated_companies', 0)} companies "
                    f"and {result.get('recalculated_qs', 0)} QS's."
                )
