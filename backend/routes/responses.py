from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, QuestionResponse, Job
from schemas import ResponseCreate, ResponseBulkCreate, ResponseOut
from auth_utils import get_current_user
from scoring import recalculate_scores

router = APIRouter(prefix="/responses", tags=["responses"])

# Question definitions per role
ROLE_QUESTIONS = {
    "estimator": [
        "qs_responsiveness", "documentation_quality", "tender_type",
        "gut_feeling", "concerns", "worked_with_qs_before",
        "qs_gave_work_last_time", "notes",
    ],
    "sales": [
        "negotiations", "scope_reduction_attempt", "further_opportunity",
        "relationship_rating", "notes",
    ],
    "project_manager": [
        "client_coordination", "variations_fair", "timeline_respected",
        "documentation_issues", "work_again", "notes",
    ],
    "accounts_receivable": [
        "paid_on_time", "days_to_payment", "invoice_disputes",
        "collection_difficulty", "account_concerns", "notes",
    ],
}

# Jobs must be in these statuses for role question access
ROLE_STATUS_GATES = {
    "estimator": None,  # always allowed
    "sales": {"pursuing", "won", "in_delivery", "invoiced", "complete"},
    "project_manager": {"in_delivery", "invoiced", "complete"},
    "accounts_receivable": {"invoiced", "complete"},
}


def _check_role_access(job: Job, role: str):
    gate = ROLE_STATUS_GATES.get(role)
    if gate and job.status.value not in gate:
        raise HTTPException(
            status_code=403,
            detail=f"Job must be in status {gate} for {role} questions. Current: {job.status.value}",
        )


@router.get("/job/{job_id}", response_model=List[dict])
def get_responses_for_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return [
        {
            "id": r.id,
            "job_id": r.job_id,
            "user_id": r.user_id,
            "user_name": r.user.name if r.user else None,
            "role": r.role,
            "question_key": r.question_key,
            "response_value": r.response_value,
            "created_at": r.created_at,
        }
        for r in job.responses
    ]


@router.post("/bulk", response_model=dict)
def submit_bulk_responses(
    body: ResponseBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == body.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    role = current_user.role.value
    _check_role_access(job, role)

    saved = 0
    for item in body.responses:
        q_key = item.get("question_key")
        q_val = item.get("response_value")

        if not q_key:
            continue

        # Validate the key belongs to this role
        allowed_keys = ROLE_QUESTIONS.get(role, [])
        if role != "admin" and q_key not in allowed_keys:
            continue

        # Upsert: one response per user per question per job
        existing = (
            db.query(QuestionResponse)
            .filter(
                QuestionResponse.job_id == body.job_id,
                QuestionResponse.user_id == current_user.id,
                QuestionResponse.question_key == q_key,
            )
            .first()
        )
        if existing:
            existing.response_value = q_val
        else:
            db.add(QuestionResponse(
                job_id=body.job_id,
                user_id=current_user.id,
                role=role,
                question_key=q_key,
                response_value=q_val,
            ))
        saved += 1

    db.commit()

    # Trigger score recalculation
    if job.company_id:
        recalculate_scores("company", job.company_id, db)
    if job.qs_id:
        recalculate_scores("qs", job.qs_id, db)

    return {"saved": saved, "job_id": body.job_id}


@router.post("", response_model=dict, status_code=201)
def submit_response(
    body: ResponseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == body.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    role = current_user.role.value
    _check_role_access(job, role)

    existing = (
        db.query(QuestionResponse)
        .filter(
            QuestionResponse.job_id == body.job_id,
            QuestionResponse.user_id == current_user.id,
            QuestionResponse.question_key == body.question_key,
        )
        .first()
    )
    if existing:
        existing.response_value = body.response_value
        db.commit()
        result = existing
    else:
        resp = QuestionResponse(
            job_id=body.job_id,
            user_id=current_user.id,
            role=role,
            question_key=body.question_key,
            response_value=body.response_value,
        )
        db.add(resp)
        db.commit()
        db.refresh(resp)
        result = resp

    if job.company_id:
        recalculate_scores("company", job.company_id, db)
    if job.qs_id:
        recalculate_scores("qs", job.qs_id, db)

    return {"id": result.id, "question_key": result.question_key, "response_value": result.response_value}
