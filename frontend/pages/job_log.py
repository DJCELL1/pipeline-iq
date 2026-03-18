"""
Job Log — full searchable/filterable job list, click-in for detail.
"""
import streamlit as st
import pandas as pd
from utils.auth import require_auth, get_user, get_role, has_role
from utils import api_client as api

STATUS_OPTIONS = ["", "at_quote", "pursuing", "won", "lost", "in_delivery", "invoiced", "complete"]
STATUS_LABELS  = {
    "": "All Statuses",
    "at_quote":    "📝 At Quote",
    "pursuing":    "🎯 Pursuing",
    "won":         "✅ Won",
    "lost":        "❌ Lost",
    "in_delivery": "🔨 In Delivery",
    "invoiced":    "💰 Invoiced",
    "complete":    "🏁 Complete",
}

QUESTION_LABELS = {
    "qs_responsiveness":       "QS Responsiveness",
    "documentation_quality":   "Documentation Quality",
    "tender_type":             "Tender Type",
    "gut_feeling":             "Gut Feeling",
    "concerns":                "Concerns",
    "worked_with_qs_before":   "Worked with QS before?",
    "qs_gave_work_last_time":  "QS gave work last time?",
    "notes":                   "Notes",
    "negotiations":            "Negotiations",
    "scope_reduction_attempt": "Scope/Margin reduction attempt?",
    "further_opportunity":     "Further opportunity?",
    "relationship_rating":     "Relationship Rating",
    "client_coordination":     "Client Coordination (site)",
    "variations_fair":         "Variations fair?",
    "timeline_respected":      "Timeline respected?",
    "documentation_issues":    "Documentation Issues",
    "work_again":              "Work again?",
    "paid_on_time":            "Paid on time?",
    "days_to_payment":         "Days to Payment",
    "invoice_disputes":        "Invoice Disputes?",
    "collection_difficulty":   "Collection Difficulty",
    "account_concerns":        "Account Concerns",
}

ROLE_QUESTION_KEYS = {
    "estimator":          ["qs_responsiveness","documentation_quality","tender_type","gut_feeling",
                           "concerns","worked_with_qs_before","qs_gave_work_last_time","notes"],
    "sales":              ["negotiations","scope_reduction_attempt","further_opportunity",
                           "relationship_rating","notes"],
    "project_manager":    ["client_coordination","variations_fair","timeline_respected",
                           "documentation_issues","work_again","notes"],
    "accounts_receivable":["paid_on_time","days_to_payment","invoice_disputes",
                           "collection_difficulty","account_concerns","notes"],
}

ROLE_STATUS_GATE = {
    "sales":              {"pursuing","won","in_delivery","invoiced","complete"},
    "project_manager":    {"in_delivery","invoiced","complete"},
    "accounts_receivable":{"invoiced","complete"},
}


def show_job_detail(job_id: int):
    job = api.get_job(job_id)
    if not job:
        st.error("Job not found.")
        return

    col_back, col_status = st.columns([3, 1])
    with col_back:
        if st.button("← Back to Job Log"):
            st.session_state.pop("selected_job_id", None)
            st.rerun()

    with col_status:
        new_status = st.selectbox("Status", STATUS_OPTIONS[1:],
                                  index=STATUS_OPTIONS[1:].index(job["status"]) if job["status"] in STATUS_OPTIONS[1:] else 0,
                                  format_func=lambda s: STATUS_LABELS.get(s, s))
        if new_status != job["status"]:
            loss_reason = None
            if new_status == "lost":
                loss_reason = st.text_input("Loss reason")
            if st.button("Update Status"):
                api.update_job(job_id, {"status": new_status, "loss_reason": loss_reason})
                st.rerun()

    st.title(f"{job['job_number']} — {job['job_name']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Company", job.get("company_name") or "—")
    c2.metric("QS",      job.get("qs_name") or "—")
    c3.metric("Value",   f"${job['quote_value']:,.0f}" if job.get("quote_value") else "—")
    c4.metric("Status",  STATUS_LABELS.get(job["status"], job["status"]))

    st.divider()

    col_resp, col_comm = st.columns([3, 2])

    with col_resp:
        st.subheader("Question Responses by Role")
        responses = job.get("responses", [])
        by_role = {}
        for r in responses:
            by_role.setdefault(r["role"], []).append(r)

        role_order = ["estimator", "sales", "project_manager", "accounts_receivable"]
        role_labels = {"estimator": "📐 Estimator", "sales": "💼 Sales",
                       "project_manager": "🔨 PM", "accounts_receivable": "💰 AR"}

        for role in role_order:
            resps = by_role.get(role, [])
            if resps:
                with st.expander(f"{role_labels.get(role, role)} ({len(resps)} responses)", expanded=True):
                    for r in resps:
                        label = QUESTION_LABELS.get(r["question_key"], r["question_key"])
                        val   = r.get("response_value") or "—"
                        author = r.get("user_name") or "Unknown"
                        st.markdown(f"**{label}:** {val}  <span style='color:#888;font-size:0.8em'>— {author}</span>",
                                    unsafe_allow_html=True)

        # ── Answer questions form ─────────────────────────────────────────────
        role = get_role()
        my_keys = ROLE_QUESTION_KEYS.get(role, [])
        status_gate = ROLE_STATUS_GATE.get(role, set())

        can_answer = (not status_gate) or (job["status"] in status_gate)

        if my_keys and can_answer:
            st.subheader(f"Your Answers ({role.replace('_', ' ').title()})")
            existing = {r["question_key"]: r["response_value"] for r in by_role.get(role, [])}
            with st.form(f"job_form_{job_id}"):
                answers = {}
                for key in my_keys:
                    label = QUESTION_LABELS.get(key, key)
                    current = existing.get(key, "")
                    if key in ("qs_responsiveness", "documentation_quality", "relationship_rating", "client_coordination"):
                        answers[key] = str(st.slider(label, 1, 5, value=int(current) if current else 3))
                    elif key in ("tender_type",):
                        opts = ["Competitive", "Relationship", "Unknown"]
                        answers[key] = st.selectbox(label, opts, index=opts.index(current) if current in opts else 0)
                    elif key in ("gut_feeling",):
                        opts = ["High", "Medium", "Low"]
                        answers[key] = st.selectbox(label, opts, index=opts.index(current) if current in opts else 1)
                    elif key in ("worked_with_qs_before",):
                        opts = ["Yes", "No"]
                        answers[key] = st.selectbox(label, opts, index=opts.index(current) if current in opts else 1)
                    elif key in ("qs_gave_work_last_time",):
                        opts = ["Yes", "No", "First time"]
                        answers[key] = st.selectbox(label, opts, index=opts.index(current) if current in opts else 2)
                    elif key in ("negotiations",):
                        opts = ["Smooth", "Some pushback", "Difficult"]
                        answers[key] = st.selectbox(label, opts, index=opts.index(current) if current in opts else 0)
                    elif key in ("scope_reduction_attempt", "invoice_disputes"):
                        opts = ["Yes", "No"]
                        answers[key] = st.selectbox(label, opts, index=opts.index(current) if current in opts else 1)
                    elif key in ("further_opportunity", "work_again"):
                        opts = ["Yes", "No", "Maybe"]
                        answers[key] = st.selectbox(label, opts, index=opts.index(current) if current in opts else 2)
                    elif key in ("variations_fair",):
                        opts = ["Yes", "No", "Not applicable"]
                        answers[key] = st.selectbox(label, opts, index=opts.index(current) if current in opts else 0)
                    elif key in ("timeline_respected",):
                        opts = ["Yes", "No"]
                        answers[key] = st.selectbox(label, opts, index=opts.index(current) if current in opts else 0)
                    elif key in ("paid_on_time",):
                        opts = ["Yes", "No", "Partially"]
                        answers[key] = st.selectbox(label, opts, index=opts.index(current) if current in opts else 0)
                    elif key == "days_to_payment":
                        answers[key] = str(st.number_input(label, min_value=0, value=int(current) if current else 30))
                    elif key == "collection_difficulty":
                        opts = ["Easy", "Some follow-up needed", "Very difficult"]
                        answers[key] = st.selectbox(label, opts, index=opts.index(current) if current in opts else 0)
                    else:
                        answers[key] = st.text_area(label, value=current, height=70)

                if st.form_submit_button("Save My Answers", use_container_width=True):
                    responses_to_save = [{"question_key": k, "response_value": v} for k, v in answers.items()]
                    result = api.submit_responses(job_id, responses_to_save)
                    if result:
                        st.success(f"Saved {result.get('saved')} responses.")
                        st.rerun()
        elif my_keys and not can_answer:
            st.info(f"Your questions are unlocked when job is in: {', '.join(status_gate)}")

    with col_comm:
        st.subheader("Comments")
        comments = api.get_comments("job", job_id)
        for c in comments:
            st.markdown(
                f"**{c['user_name']}**  "
                f"<span style='color:#888;font-size:0.8em'>{c['created_at'][:10]}</span>",
                unsafe_allow_html=True,
            )
            st.write(c["body"])
            st.divider()

        with st.form("new_comment_job"):
            new_body = st.text_area("Add a comment", height=80, label_visibility="collapsed",
                                    placeholder="Leave a note…")
            if st.form_submit_button("Post Comment"):
                if new_body.strip():
                    api.add_comment("job", job_id, new_body.strip())
                    st.rerun()


def show():
    require_auth()

    # If a specific job is selected, show its detail
    selected_job_id = st.session_state.get("selected_job_id")
    if selected_job_id:
        show_job_detail(selected_job_id)
        return

    st.title("Job Log")

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.expander("Filters", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            search  = st.text_input("Search job name / number", placeholder="Type to search…")
            status  = st.selectbox("Status", STATUS_OPTIONS, format_func=lambda s: STATUS_LABELS.get(s, "All"))
        with fc2:
            companies = api.get_companies()
            co_map  = {"All": None}
            co_map.update({c["name"]: c["id"] for c in companies})
            sel_co  = st.selectbox("Company", list(co_map.keys()))

            all_qs  = api.get_qs_list()
            qs_map  = {"All": None}
            qs_map.update({q["name"]: q["id"] for q in all_qs})
            sel_qs  = st.selectbox("QS", list(qs_map.keys()))
        with fc3:
            date_from = st.date_input("Quote from", value=None)
            date_to   = st.date_input("Quote to",   value=None)

    jobs = api.get_jobs(
        search=search,
        status=status,
        company_id=co_map.get(sel_co),
        qs_id=qs_map.get(sel_qs),
        date_from=str(date_from) if date_from else "",
        date_to=str(date_to)   if date_to   else "",
    )

    if not jobs:
        st.info("No jobs found matching the filters.")
        if has_role("estimator", "admin"):
            if st.button("+ Create Job Manually"):
                st.session_state["show_create_job"] = True
        return

    # ── Create job form ───────────────────────────────────────────────────────
    if has_role("estimator", "admin"):
        with st.expander("+ Create Job Manually", expanded=st.session_state.get("show_create_job", False)):
            with st.form("create_job"):
                jc1, jc2 = st.columns(2)
                with jc1:
                    j_num  = st.text_input("Job Number")
                    j_name = st.text_input("Job Name")
                    j_co   = st.selectbox("Company", ["(None)"] + list(co_map.keys())[1:])
                with jc2:
                    j_qs   = st.selectbox("QS", ["(None)"] + list(qs_map.keys())[1:])
                    j_val  = st.number_input("Quote Value", min_value=0.0, step=1000.0)
                    j_date = st.date_input("Quote Date")
                if st.form_submit_button("Create Job"):
                    if j_num and j_name:
                        api.create_job({
                            "job_number": j_num,
                            "job_name":   j_name,
                            "company_id": co_map.get(j_co),
                            "qs_id":      qs_map.get(j_qs),
                            "quote_value": j_val or None,
                            "quote_date":  str(j_date) if j_date else None,
                        })
                        st.session_state.pop("show_create_job", None)
                        st.rerun()

    # ── Job table ─────────────────────────────────────────────────────────────
    st.caption(f"{len(jobs)} job(s) found")

    rows = []
    for j in jobs:
        rows.append({
            "_id":      j["id"],
            "Job #":    j["job_number"],
            "Job Name": j["job_name"][:55],
            "Company":  j.get("company_name") or "—",
            "QS":       j.get("qs_name") or "—",
            "Value":    f"${j['quote_value']:,.0f}" if j.get("quote_value") else "—",
            "Date":     j.get("quote_date", "")[:10] if j.get("quote_date") else "—",
            "Status":   STATUS_LABELS.get(j["status"], j["status"]),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df.drop(columns=["_id"]), use_container_width=True, height=400, hide_index=True)

    st.divider()
    selected_label = st.selectbox("Open Job →", [f"{r['Job #']} — {r['Job Name']}" for r in rows],
                                  label_visibility="collapsed")
    if st.button("Open Job Detail →"):
        idx = next(i for i, r in enumerate(rows) if f"{r['Job #']} — {r['Job Name']}" == selected_label)
        st.session_state["selected_job_id"] = rows[idx]["_id"]
        st.rerun()
