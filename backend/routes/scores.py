from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, Score, ScoreWeight, FlagConfig, Company, QuantitySurveyor
from schemas import ScoreWeightUpdate, FlagConfigUpdate
from auth_utils import get_current_user, require_admin
from scoring import recalculate_scores, get_entity_scores, DEFAULT_WEIGHTS, DEFAULT_FLAG_THRESHOLDS
from datetime import datetime

router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("/{entity_type}/{entity_id}")
def get_scores(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if entity_type not in ("company", "qs"):
        raise HTTPException(status_code=400, detail="entity_type must be company or qs")
    return get_entity_scores(entity_type, entity_id, db)


@router.post("/recalculate/{entity_type}/{entity_id}")
def recalculate(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if entity_type not in ("company", "qs"):
        raise HTTPException(status_code=400, detail="entity_type must be company or qs")
    return recalculate_scores(entity_type, entity_id, db)


@router.post("/recalculate-all")
def recalculate_all(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    companies = db.query(Company).all()
    qss = db.query(QuantitySurveyor).all()
    for c in companies:
        recalculate_scores("company", c.id, db)
    for q in qss:
        recalculate_scores("qs", q.id, db)
    return {"recalculated_companies": len(companies), "recalculated_qs": len(qss)}


@router.get("/weights")
def get_weights(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = db.query(ScoreWeight).all()
    if not rows:
        return DEFAULT_WEIGHTS
    return {r.dimension: r.weight for r in rows}


@router.put("/weights")
def update_weights(
    body: ScoreWeightUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    weights = body.model_dump()
    for dim, weight in weights.items():
        existing = db.query(ScoreWeight).filter(ScoreWeight.dimension == dim).first()
        if existing:
            existing.weight = weight
            existing.updated_at = datetime.utcnow()
        else:
            db.add(ScoreWeight(dimension=dim, weight=weight))
    db.commit()
    return weights


@router.get("/flag-config")
def get_flag_config(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = db.query(FlagConfig).all()
    if not rows:
        return DEFAULT_FLAG_THRESHOLDS
    return {r.flag_key: r.threshold_value for r in rows}


@router.put("/flag-config")
def update_flag_config(
    body: FlagConfigUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    configs = body.model_dump()
    for key, val in configs.items():
        existing = db.query(FlagConfig).filter(FlagConfig.flag_key == key).first()
        if existing:
            existing.threshold_value = val
            existing.updated_at = datetime.utcnow()
        else:
            db.add(FlagConfig(flag_key=key, threshold_value=val))
    db.commit()
    return configs


@router.post("/override/{entity_type}/{entity_id}/{dimension}")
def override_score(
    entity_type: str,
    entity_id: int,
    dimension: str,
    score: float,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin can manually override a score."""
    existing = (
        db.query(Score)
        .filter(
            Score.entity_type == entity_type,
            Score.entity_id == entity_id,
            Score.dimension == dimension,
        )
        .first()
    )
    if existing:
        existing.score = min(10.0, max(0.0, score))
        existing.calculated_at = datetime.utcnow()
    else:
        db.add(Score(
            entity_type=entity_type,
            entity_id=entity_id,
            dimension=dimension,
            score=min(10.0, max(0.0, score)),
        ))
    db.commit()
    return {"entity_type": entity_type, "entity_id": entity_id, "dimension": dimension, "score": score}
