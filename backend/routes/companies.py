from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import User, Company, Job
from schemas import CompanyCreate, CompanyUpdate, CompanyOut
from auth_utils import get_current_user
from scoring import recalculate_scores, get_entity_scores

router = APIRouter(prefix="/companies", tags=["companies"])


def _enrich(company: Company, db: Session) -> dict:
    data = {
        "id": company.id,
        "name": company.name,
        "segment": company.segment,
        "created_at": company.created_at,
    }
    info = get_entity_scores("company", company.id, db)
    data["scores"] = info["scores"]
    data["flags"] = info["flags"]
    return data


@router.get("", response_model=List[dict])
def list_companies(
    search: Optional[str] = Query(None),
    segment: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Company)
    if search:
        q = q.filter(Company.name.ilike(f"%{search}%"))
    if segment:
        q = q.filter(Company.segment == segment)
    companies = q.order_by(Company.name).all()
    return [_enrich(c, db) for c in companies]


@router.post("", response_model=dict, status_code=201)
def create_company(
    body: CompanyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    company = Company(**body.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return _enrich(company, db)


@router.get("/{company_id}", response_model=dict)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    data = _enrich(company, db)

    # Include linked QS's
    data["quantity_surveyors"] = [
        {"id": qs.id, "name": qs.name, "email": qs.email, "phone": qs.phone}
        for qs in company.quantity_surveyors
    ]

    # Include job history
    jobs = db.query(Job).filter(Job.company_id == company_id).order_by(Job.created_at.desc()).all()
    data["jobs"] = [
        {
            "id": j.id,
            "job_number": j.job_number,
            "job_name": j.job_name,
            "quote_value": j.quote_value,
            "quote_date": j.quote_date,
            "status": j.status.value,
            "qs_name": j.qs.name if j.qs else None,
        }
        for j in jobs
    ]

    return data


@router.put("/{company_id}", response_model=dict)
def update_company(
    company_id: int,
    body: CompanyUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(company, k, v)
    db.commit()
    db.refresh(company)
    return _enrich(company, db)


@router.delete("/{company_id}", status_code=204)
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()


@router.post("/{company_id}/recalculate")
def recalculate(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return recalculate_scores("company", company_id, db)
