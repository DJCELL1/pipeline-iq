from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import User, QuantitySurveyor, Job, Company
from schemas import QSCreate, QSUpdate
from auth_utils import get_current_user
from scoring import recalculate_scores, get_entity_scores

router = APIRouter(prefix="/qs", tags=["quantity_surveyors"])


def _enrich(qs: QuantitySurveyor, db: Session) -> dict:
    info = get_entity_scores("qs", qs.id, db)
    jobs = db.query(Job).filter(Job.qs_id == qs.id).all()
    total = len(jobs)
    won = sum(1 for j in jobs if j.status.value in ["won", "in_delivery", "invoiced", "complete"])
    win_rate = round(won / total, 2) if total > 0 else None
    return {
        "id": qs.id,
        "name": qs.name,
        "email": qs.email,
        "phone": qs.phone,
        "company_id": qs.company_id,
        "company_name": qs.company.name if qs.company else None,
        "created_at": qs.created_at,
        "total_jobs": total,
        "won_jobs": won,
        "win_rate": win_rate,
        "scores": info["scores"],
        "flags": info["flags"],
    }


@router.get("", response_model=List[dict])
def list_qs(
    search: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(QuantitySurveyor)
    if search:
        q = q.filter(QuantitySurveyor.name.ilike(f"%{search}%"))
    if company_id:
        q = q.filter(QuantitySurveyor.company_id == company_id)
    qss = q.order_by(QuantitySurveyor.name).all()
    return [_enrich(qs, db) for qs in qss]


@router.post("", response_model=dict, status_code=201)
def create_qs(
    body: QSCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    qs = QuantitySurveyor(**body.model_dump())
    db.add(qs)
    db.commit()
    db.refresh(qs)
    return _enrich(qs, db)


@router.get("/leaderboard", response_model=List[dict])
def qs_leaderboard(
    company_id: Optional[int] = Query(None),
    flag: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(QuantitySurveyor)
    if company_id:
        q = q.filter(QuantitySurveyor.company_id == company_id)
    all_qs = q.all()
    enriched = [_enrich(qs, db) for qs in all_qs]
    if flag:
        enriched = [e for e in enriched if flag in e["flags"]]
    enriched.sort(key=lambda e: (e["scores"].get("overall_score") or -1), reverse=True)
    return enriched


@router.get("/{qs_id}", response_model=dict)
def get_qs(
    qs_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    qs = db.query(QuantitySurveyor).filter(QuantitySurveyor.id == qs_id).first()
    if not qs:
        raise HTTPException(status_code=404, detail="QS not found")

    data = _enrich(qs, db)

    # Job history
    jobs = db.query(Job).filter(Job.qs_id == qs_id).order_by(Job.created_at.desc()).all()
    data["jobs"] = [
        {
            "id": j.id,
            "job_number": j.job_number,
            "job_name": j.job_name,
            "quote_value": j.quote_value,
            "quote_date": j.quote_date,
            "status": j.status.value,
            "company_name": j.company.name if j.company else None,
        }
        for j in jobs
    ]
    return data


@router.put("/{qs_id}", response_model=dict)
def update_qs(
    qs_id: int,
    body: QSUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    qs = db.query(QuantitySurveyor).filter(QuantitySurveyor.id == qs_id).first()
    if not qs:
        raise HTTPException(status_code=404, detail="QS not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(qs, k, v)
    db.commit()
    db.refresh(qs)
    return _enrich(qs, db)


@router.delete("/{qs_id}", status_code=204)
def delete_qs(
    qs_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    qs = db.query(QuantitySurveyor).filter(QuantitySurveyor.id == qs_id).first()
    if not qs:
        raise HTTPException(status_code=404, detail="QS not found")
    db.delete(qs)
    db.commit()


@router.post("/{qs_id}/recalculate")
def recalculate(
    qs_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    qs = db.query(QuantitySurveyor).filter(QuantitySurveyor.id == qs_id).first()
    if not qs:
        raise HTTPException(status_code=404, detail="QS not found")
    return recalculate_scores("qs", qs_id, db)
