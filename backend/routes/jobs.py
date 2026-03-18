from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import pandas as pd

from database import get_db
from models import User, Job, JobStatus, Company, QuantitySurveyor
from schemas import JobCreate, JobUpdate, JobImportRow
from auth_utils import get_current_user
from scoring import recalculate_scores

router = APIRouter(prefix="/jobs", tags=["jobs"])

WON_STATUSES = {"won", "in_delivery", "invoiced", "complete"}


def _job_out(job: Job) -> dict:
    return {
        "id": job.id,
        "job_number": job.job_number,
        "job_name": job.job_name,
        "company_id": job.company_id,
        "company_name": job.company.name if job.company else None,
        "qs_id": job.qs_id,
        "qs_name": job.qs.name if job.qs else None,
        "quote_value": job.quote_value,
        "quote_date": job.quote_date,
        "status": job.status.value,
        "loss_reason": job.loss_reason,
        "created_at": job.created_at,
    }


def _trigger_recalc(job: Job, db: Session):
    if job.company_id:
        recalculate_scores("company", job.company_id, db)
    if job.qs_id:
        recalculate_scores("qs", job.qs_id, db)


@router.get("", response_model=List[dict])
def list_jobs(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    qs_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    value_min: Optional[float] = Query(None),
    value_max: Optional[float] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Job)
    if search:
        q = q.filter(
            Job.job_name.ilike(f"%{search}%") | Job.job_number.ilike(f"%{search}%")
        )
    if status:
        try:
            q = q.filter(Job.status == JobStatus(status))
        except ValueError:
            pass
    if company_id:
        q = q.filter(Job.company_id == company_id)
    if qs_id:
        q = q.filter(Job.qs_id == qs_id)
    if date_from:
        q = q.filter(Job.quote_date >= datetime.fromisoformat(date_from))
    if date_to:
        q = q.filter(Job.quote_date <= datetime.fromisoformat(date_to))
    if value_min is not None:
        q = q.filter(Job.quote_value >= value_min)
    if value_max is not None:
        q = q.filter(Job.quote_value <= value_max)

    jobs = q.order_by(Job.created_at.desc()).all()
    return [_job_out(j) for j in jobs]


@router.post("", response_model=dict, status_code=201)
def create_job(
    body: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Job).filter(Job.job_number == body.job_number).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Job number {body.job_number} already exists")

    job = Job(**body.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    _trigger_recalc(job, db)
    return _job_out(job)


@router.get("/pending-questions", response_model=List[dict])
def pending_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return jobs where the current user's role has unanswered questions."""
    role = current_user.role.value
    result = []

    if role in ("estimator", "admin"):
        # All jobs need estimator questions
        jobs = db.query(Job).all()
        est_questions = [
            "qs_responsiveness", "documentation_quality", "tender_type",
            "gut_feeling", "concerns", "worked_with_qs_before",
            "qs_gave_work_last_time", "notes",
        ]
        for job in jobs:
            answered = {
                r.question_key
                for r in job.responses
                if r.role == "estimator"
            }
            missing = [q for q in est_questions if q not in answered]
            if missing:
                result.append({**_job_out(job), "pending_role": "estimator", "missing_questions": missing})

    if role in ("sales", "admin"):
        won_pursuing = db.query(Job).filter(
            Job.status.in_([JobStatus.WON, JobStatus.PURSUING, JobStatus.IN_DELIVERY,
                            JobStatus.INVOICED, JobStatus.COMPLETE])
        ).all()
        sales_questions = ["negotiations", "scope_reduction_attempt", "further_opportunity",
                           "relationship_rating", "notes"]
        for job in won_pursuing:
            answered = {r.question_key for r in job.responses if r.role == "sales"}
            missing = [q for q in sales_questions if q not in answered]
            if missing:
                result.append({**_job_out(job), "pending_role": "sales", "missing_questions": missing})

    if role in ("project_manager", "admin"):
        delivery_jobs = db.query(Job).filter(
            Job.status.in_([JobStatus.IN_DELIVERY, JobStatus.INVOICED, JobStatus.COMPLETE])
        ).all()
        pm_questions = ["client_coordination", "variations_fair", "timeline_respected",
                        "documentation_issues", "work_again", "notes"]
        for job in delivery_jobs:
            answered = {r.question_key for r in job.responses if r.role == "project_manager"}
            missing = [q for q in pm_questions if q not in answered]
            if missing:
                result.append({**_job_out(job), "pending_role": "project_manager", "missing_questions": missing})

    if role in ("accounts_receivable", "admin"):
        invoiced_jobs = db.query(Job).filter(
            Job.status.in_([JobStatus.INVOICED, JobStatus.COMPLETE])
        ).all()
        ar_questions = ["paid_on_time", "days_to_payment", "invoice_disputes",
                        "collection_difficulty", "account_concerns", "notes"]
        for job in invoiced_jobs:
            answered = {r.question_key for r in job.responses if r.role == "accounts_receivable"}
            missing = [q for q in ar_questions if q not in answered]
            if missing:
                result.append({**_job_out(job), "pending_role": "accounts_receivable", "missing_questions": missing})

    return result


@router.get("/dashboard-stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from datetime import date
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)

    all_jobs = db.query(Job).all()
    active = [j for j in all_jobs if j.status.value not in ("lost", "complete")]
    pipeline_value = sum(j.quote_value or 0 for j in active)

    closed = [j for j in all_jobs if j.status.value in WON_STATUSES | {"lost"}]
    won = [j for j in closed if j.status.value in WON_STATUSES]
    win_rate = round(len(won) / len(closed), 3) if closed else 0.0

    jobs_this_month = [j for j in all_jobs if j.created_at and j.created_at >= month_start]

    companies_count = db.query(Company).count()
    qs_count = db.query(QuantitySurveyor).count()

    return {
        "total_pipeline_value": pipeline_value,
        "win_rate": win_rate,
        "jobs_this_month": len(jobs_this_month),
        "active_jobs": len(active),
        "total_companies": companies_count,
        "total_qs": qs_count,
    }


@router.get("/analytics/win-loss-by-month")
def win_loss_by_month(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    jobs = db.query(Job).filter(Job.quote_date.isnot(None)).all()
    data = {}
    for j in jobs:
        key = j.quote_date.strftime("%Y-%m")
        if key not in data:
            data[key] = {"month": key, "won": 0, "lost": 0, "other": 0}
        if j.status.value in WON_STATUSES:
            data[key]["won"] += 1
        elif j.status.value == "lost":
            data[key]["lost"] += 1
        else:
            data[key]["other"] += 1
    return sorted(data.values(), key=lambda x: x["month"])


@router.get("/analytics/loss-reasons")
def loss_reasons(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    lost_jobs = db.query(Job).filter(Job.status == JobStatus.LOST).all()
    reasons = {}
    for j in lost_jobs:
        reason = j.loss_reason or "Not specified"
        reasons[reason] = reasons.get(reason, 0) + 1
    return [{"reason": k, "count": v} for k, v in sorted(reasons.items(), key=lambda x: -x[1])]


@router.get("/analytics/top-companies-by-value")
def top_companies(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    jobs = db.query(Job).filter(Job.company_id.isnot(None), Job.quote_value.isnot(None)).all()
    companies = {}
    for j in jobs:
        cname = j.company.name if j.company else "Unknown"
        if cname not in companies:
            companies[cname] = 0
        companies[cname] += j.quote_value
    return sorted(
        [{"company": k, "total_value": v} for k, v in companies.items()],
        key=lambda x: -x["total_value"]
    )[:10]


@router.get("/{job_id}", response_model=dict)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    data = _job_out(job)
    data["responses"] = [
        {
            "id": r.id,
            "user_id": r.user_id,
            "user_name": r.user.name if r.user else None,
            "role": r.role,
            "question_key": r.question_key,
            "response_value": r.response_value,
            "created_at": r.created_at,
        }
        for r in job.responses
    ]
    return data


@router.put("/{job_id}", response_model=dict)
def update_job(
    job_id: int,
    body: JobUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(job, k, v)
    db.commit()
    db.refresh(job)
    _trigger_recalc(job, db)
    return _job_out(job)


@router.delete("/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    company_id = job.company_id
    qs_id = job.qs_id
    db.delete(job)
    db.commit()
    if company_id:
        recalculate_scores("company", company_id, db)
    if qs_id:
        recalculate_scores("qs", qs_id, db)


@router.post("/import", response_model=dict)
def import_jobs(
    rows: List[JobImportRow],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    imported = []
    skipped = []
    errors = []

    for row in rows:
        try:
            # Duplicate check
            existing = db.query(Job).filter(Job.job_number == row.job_number).first()
            if existing:
                skipped.append(row.job_number)
                continue

            # Resolve or create company
            company_id = None
            if row.company_name:
                company = db.query(Company).filter(
                    Company.name.ilike(row.company_name)
                ).first()
                if not company:
                    company = Company(name=row.company_name)
                    db.add(company)
                    db.flush()
                company_id = company.id

            # Resolve or create QS
            qs_id = None
            if row.qs_name:
                qs = db.query(QuantitySurveyor).filter(
                    QuantitySurveyor.name.ilike(row.qs_name)
                ).first()
                if not qs:
                    qs = QuantitySurveyor(name=row.qs_name, company_id=company_id)
                    db.add(qs)
                    db.flush()
                qs_id = qs.id

            # Parse date
            quote_date = None
            if row.quote_date:
                try:
                    quote_date = datetime.fromisoformat(row.quote_date)
                except ValueError:
                    try:
                        quote_date = datetime.strptime(row.quote_date, "%d/%m/%Y")
                    except ValueError:
                        pass

            # Parse status
            status = JobStatus.AT_QUOTE
            if row.status:
                status_map = {
                    "at quote": JobStatus.AT_QUOTE,
                    "pursuing": JobStatus.PURSUING,
                    "won": JobStatus.WON,
                    "lost": JobStatus.LOST,
                    "in delivery": JobStatus.IN_DELIVERY,
                    "invoiced": JobStatus.INVOICED,
                    "complete": JobStatus.COMPLETE,
                }
                status = status_map.get(row.status.lower(), JobStatus.AT_QUOTE)

            job = Job(
                job_number=row.job_number,
                job_name=row.job_name,
                company_id=company_id,
                qs_id=qs_id,
                quote_value=row.quote_value,
                quote_date=quote_date,
                status=status,
            )
            db.add(job)
            db.flush()
            imported.append(row.job_number)

        except Exception as e:
            errors.append({"job_number": row.job_number, "error": str(e)})

    db.commit()

    # Recalculate all affected scores
    for company in db.query(Company).all():
        recalculate_scores("company", company.id, db)
    for qs in db.query(QuantitySurveyor).all():
        recalculate_scores("qs", qs.id, db)

    return {"imported": len(imported), "skipped": len(skipped), "errors": errors,
            "imported_numbers": imported, "skipped_numbers": skipped}
