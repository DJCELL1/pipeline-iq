"""
Centralised API client for all FastAPI calls.
All network communication from Streamlit goes through this module.
"""
import os
import requests
import streamlit as st
from typing import Any, Optional

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _headers() -> dict:
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _handle(response: requests.Response) -> Any:
    if response.status_code == 401:
        # No auth required - just return None silently
        return None
    if response.status_code == 403:
        st.error("You don't have permission to perform that action.")
        return None
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        st.error(f"API error {response.status_code}: {detail}")
        return None
    if response.status_code == 204:
        return True
    return response.json()


# ── Auth ──────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> Optional[dict]:
    try:
        r = requests.post(f"{BACKEND_URL}/auth/login", json={"email": email, "password": password})
        return _handle(r)
    except requests.ConnectionError:
        st.error("Cannot connect to backend. Make sure the API is running.")
        return None


# ── Companies ─────────────────────────────────────────────────────────────────

def get_companies(search: str = "", segment: str = "") -> list:
    params = {}
    if search:
        params["search"] = search
    if segment:
        params["segment"] = segment
    r = requests.get(f"{BACKEND_URL}/companies", headers=_headers(), params=params)
    return _handle(r) or []


def get_company(company_id: int) -> Optional[dict]:
    r = requests.get(f"{BACKEND_URL}/companies/{company_id}", headers=_headers())
    return _handle(r)


def create_company(name: str, segment: str = "") -> Optional[dict]:
    r = requests.post(f"{BACKEND_URL}/companies", headers=_headers(),
                      json={"name": name, "segment": segment or None})
    return _handle(r)


def update_company(company_id: int, data: dict) -> Optional[dict]:
    r = requests.put(f"{BACKEND_URL}/companies/{company_id}", headers=_headers(), json=data)
    return _handle(r)


def recalculate_company(company_id: int) -> Optional[dict]:
    r = requests.post(f"{BACKEND_URL}/companies/{company_id}/recalculate", headers=_headers())
    return _handle(r)


# ── Quantity Surveyors ────────────────────────────────────────────────────────

def get_qs_list(search: str = "", company_id: int = None) -> list:
    params = {}
    if search:
        params["search"] = search
    if company_id:
        params["company_id"] = company_id
    r = requests.get(f"{BACKEND_URL}/qs", headers=_headers(), params=params)
    return _handle(r) or []


def get_qs(qs_id: int) -> Optional[dict]:
    r = requests.get(f"{BACKEND_URL}/qs/{qs_id}", headers=_headers())
    return _handle(r)


def get_qs_leaderboard(company_id: int = None, flag: str = "") -> list:
    params = {}
    if company_id:
        params["company_id"] = company_id
    if flag:
        params["flag"] = flag
    r = requests.get(f"{BACKEND_URL}/qs/leaderboard", headers=_headers(), params=params)
    return _handle(r) or []


def create_qs(data: dict) -> Optional[dict]:
    r = requests.post(f"{BACKEND_URL}/qs", headers=_headers(), json=data)
    return _handle(r)


def update_qs(qs_id: int, data: dict) -> Optional[dict]:
    r = requests.put(f"{BACKEND_URL}/qs/{qs_id}", headers=_headers(), json=data)
    return _handle(r)


# ── Jobs ──────────────────────────────────────────────────────────────────────

def get_jobs(search="", status="", company_id=None, qs_id=None,
             date_from="", date_to="", value_min=None, value_max=None) -> list:
    params = {}
    if search:      params["search"] = search
    if status:      params["status"] = status
    if company_id:  params["company_id"] = company_id
    if qs_id:       params["qs_id"] = qs_id
    if date_from:   params["date_from"] = date_from
    if date_to:     params["date_to"] = date_to
    if value_min is not None: params["value_min"] = value_min
    if value_max is not None: params["value_max"] = value_max
    r = requests.get(f"{BACKEND_URL}/jobs", headers=_headers(), params=params)
    return _handle(r) or []


def get_job(job_id: int) -> Optional[dict]:
    r = requests.get(f"{BACKEND_URL}/jobs/{job_id}", headers=_headers())
    return _handle(r)


def get_pending_questions() -> list:
    r = requests.get(f"{BACKEND_URL}/jobs/pending-questions", headers=_headers())
    return _handle(r) or []


def create_job(data: dict) -> Optional[dict]:
    r = requests.post(f"{BACKEND_URL}/jobs", headers=_headers(), json=data)
    return _handle(r)


def update_job(job_id: int, data: dict) -> Optional[dict]:
    r = requests.put(f"{BACKEND_URL}/jobs/{job_id}", headers=_headers(), json=data)
    return _handle(r)


def import_jobs(rows: list) -> Optional[dict]:
    r = requests.post(f"{BACKEND_URL}/jobs/import", headers=_headers(), json=rows)
    return _handle(r)


def get_dashboard_stats() -> Optional[dict]:
    r = requests.get(f"{BACKEND_URL}/jobs/dashboard-stats", headers=_headers())
    return _handle(r)


def get_win_loss_by_month() -> list:
    r = requests.get(f"{BACKEND_URL}/jobs/analytics/win-loss-by-month", headers=_headers())
    return _handle(r) or []


def get_loss_reasons() -> list:
    r = requests.get(f"{BACKEND_URL}/jobs/analytics/loss-reasons", headers=_headers())
    return _handle(r) or []


def get_top_companies_by_value() -> list:
    r = requests.get(f"{BACKEND_URL}/jobs/analytics/top-companies-by-value", headers=_headers())
    return _handle(r) or []


# ── Responses ─────────────────────────────────────────────────────────────────

def get_responses(job_id: int) -> list:
    r = requests.get(f"{BACKEND_URL}/responses/job/{job_id}", headers=_headers())
    return _handle(r) or []


def submit_responses(job_id: int, responses: list) -> Optional[dict]:
    r = requests.post(f"{BACKEND_URL}/responses/bulk", headers=_headers(),
                      json={"job_id": job_id, "responses": responses})
    return _handle(r)


# ── Comments ──────────────────────────────────────────────────────────────────

def get_comments(entity_type: str, entity_id: int) -> list:
    r = requests.get(f"{BACKEND_URL}/comments",
                     headers=_headers(),
                     params={"entity_type": entity_type, "entity_id": entity_id})
    return _handle(r) or []


def add_comment(entity_type: str, entity_id: int, body: str) -> Optional[dict]:
    r = requests.post(f"{BACKEND_URL}/comments", headers=_headers(),
                      json={"entity_type": entity_type, "entity_id": entity_id, "body": body})
    return _handle(r)


def delete_comment(comment_id: int) -> bool:
    r = requests.delete(f"{BACKEND_URL}/comments/{comment_id}", headers=_headers())
    return _handle(r) is True


# ── Scores ────────────────────────────────────────────────────────────────────

def get_scores(entity_type: str, entity_id: int) -> Optional[dict]:
    r = requests.get(f"{BACKEND_URL}/scores/{entity_type}/{entity_id}", headers=_headers())
    return _handle(r)


def get_score_weights() -> dict:
    r = requests.get(f"{BACKEND_URL}/scores/weights", headers=_headers())
    return _handle(r) or {}


def update_score_weights(weights: dict) -> Optional[dict]:
    r = requests.put(f"{BACKEND_URL}/scores/weights", headers=_headers(), json=weights)
    return _handle(r)


def get_flag_config() -> dict:
    r = requests.get(f"{BACKEND_URL}/scores/flag-config", headers=_headers())
    return _handle(r) or {}


def update_flag_config(config: dict) -> Optional[dict]:
    r = requests.put(f"{BACKEND_URL}/scores/flag-config", headers=_headers(), json=config)
    return _handle(r)


def recalculate_all() -> Optional[dict]:
    r = requests.post(f"{BACKEND_URL}/scores/recalculate-all", headers=_headers())
    return _handle(r)


# ── Admin ─────────────────────────────────────────────────────────────────────

def get_users() -> list:
    r = requests.get(f"{BACKEND_URL}/admin/users", headers=_headers())
    return _handle(r) or []


def create_user(data: dict) -> Optional[dict]:
    r = requests.post(f"{BACKEND_URL}/admin/users", headers=_headers(), json=data)
    return _handle(r)


def update_user(user_id: int, data: dict) -> Optional[dict]:
    r = requests.put(f"{BACKEND_URL}/admin/users/{user_id}", headers=_headers(), json=data)
    return _handle(r)


def delete_user(user_id: int) -> bool:
    r = requests.delete(f"{BACKEND_URL}/admin/users/{user_id}", headers=_headers())
    return _handle(r) is True
