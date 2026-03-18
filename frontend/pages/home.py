"""
Home / My Actions page — shows pending question sets for the logged-in user.
"""
import streamlit as st
from utils.auth import require_auth, get_user, get_role
from utils import api_client as api

QUESTION_LABELS = {
    # Estimator
    "qs_responsiveness":       ("QS Responsiveness", "1-5 rating", "rating_1_5"),
    "documentation_quality":   ("Documentation Quality", "1-5 rating", "rating_1_5"),
    "tender_type":             ("Tender Type", "", "select", ["Competitive", "Relationship", "Unknown"]),
    "gut_feeling":             ("Gut Feeling on Chances", "", "select", ["High", "Medium", "Low"]),
    "concerns":                ("Concerns about this job/company", "", "text"),
    "worked_with_qs_before":   ("Worked with this QS before?", "", "select", ["Yes", "No"]),
    "qs_gave_work_last_time":  ("Did they give us work last time?", "", "select", ["Yes", "No", "First time"]),
    # Sales
    "negotiations":            ("How did negotiations go?", "", "select", ["Smooth", "Some pushback", "Difficult"]),
    "scope_reduction_attempt": ("Did client try to reduce scope/margin?", "", "select", ["Yes", "No"]),
    "further_opportunity":     ("Further work opportunity?", "", "select", ["Yes", "No", "Maybe"]),
    "relationship_rating":     ("Relationship Rating", "1-5 rating", "rating_1_5"),
    # PM
    "client_coordination":     ("Client Coordination (on-site)", "1-5 rating", "rating_1_5"),
    "variations_fair":         ("Variations handled fairly?", "", "select", ["Yes", "No", "Not applicable"]),
    "timeline_respected":      ("Client respecting agreed timelines?", "", "select", ["Yes", "No"]),
    "documentation_issues":    ("Documentation issues during delivery", "", "text"),
    "work_again":              ("Work with this company again?", "", "select", ["Yes", "No", "Maybe"]),
    # AR
    "paid_on_time":            ("Paid on time?", "", "select", ["Yes", "No", "Partially"]),
    "days_to_payment":         ("Days from invoice to payment", "", "number"),
    "invoice_disputes":        ("Invoice disputes?", "", "select", ["Yes", "No"]),
    "collection_difficulty":   ("Collection difficulty", "", "select", ["Easy", "Some follow-up needed", "Very difficult"]),
    "account_concerns":        ("Concerns about this account", "", "text"),
    # Shared
    "notes":                   ("Notes", "", "text"),
}


def render_question(key: str, existing_val=None):
    meta = QUESTION_LABELS.get(key)
    if not meta:
        return st.text_input(key, value=existing_val or "")

    label = meta[0]
    hint  = meta[1]
    qtype = meta[2]

    if qtype == "rating_1_5":
        return str(st.slider(label, 1, 5, value=int(existing_val) if existing_val else 3))
    elif qtype == "select":
        options = list(meta[3])
        idx = options.index(existing_val) if existing_val in options else 0
        return st.selectbox(label, options, index=idx)
    elif qtype == "number":
        return str(st.number_input(label, min_value=0, value=int(existing_val) if existing_val else 0, step=1))
    else:
        return st.text_area(label, value=existing_val or "", height=80)


def show():
    require_auth()
    user = get_user()
    role = get_role()

    st.title("My Actions")
    st.caption(f"Logged in as **{user.get('name')}** — {role.replace('_', ' ').title()}")

    pending = api.get_pending_questions()

    if not pending:
        st.success("You're all caught up! No pending questions.")
        return

    st.info(f"You have **{len(pending)}** job(s) awaiting your input.")

    for item in pending:
        job_label = f"{item['job_number']} — {item['job_name']}"
        with st.expander(f"📋 {job_label}  |  {item.get('company_name', '')}  |  {item['status'].replace('_', ' ').title()}", expanded=False):
            if item.get("quote_value"):
                st.caption(f"Quote value: ${item['quote_value']:,.0f}  |  QS: {item.get('qs_name', 'N/A')}")

            missing = item.get("missing_questions", [])
            st.markdown(f"**{len(missing)} question(s) to answer:**")

            # Build form keyed to job id
            with st.form(key=f"form_{item['id']}_{item.get('pending_role')}"):
                answers = {}
                for q_key in missing:
                    answers[q_key] = render_question(q_key)

                submitted = st.form_submit_button("Save Responses", use_container_width=True)

            if submitted:
                responses = [{"question_key": k, "response_value": v} for k, v in answers.items() if v]
                result = api.submit_responses(item["id"], responses)
                if result:
                    st.success(f"Saved {result.get('saved', 0)} response(s).")
                    st.rerun()
