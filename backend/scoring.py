"""
Pipeline IQ Scoring Engine
Calculates composite scores for Companies and QS entities across four dimensions.
All scores are on a 0–10 scale. None is returned when insufficient data exists.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models import Job, JobStatus, QuestionResponse, Score, ScoreWeight, FlagConfig, Company, QuantitySurveyor


# ── Default weights (Admin can override via DB) ───────────────────────────────

DEFAULT_WEIGHTS = {
    "win_likelihood":      0.25,
    "relationship_quality": 0.30,
    "delivery_experience": 0.25,
    "payment_reliability": 0.20,
}

DEFAULT_FLAG_THRESHOLDS = {
    "payment_risk_threshold": 4.0,
    "cold_months":            6.0,
    "loss_streak_count":      3.0,
    "loyal_win_rate":         0.6,
}

# Status values that count as "won"
WON_STATUSES = {JobStatus.WON, JobStatus.IN_DELIVERY, JobStatus.INVOICED, JobStatus.COMPLETE}
LOST_STATUSES = {JobStatus.LOST}


def _get_weights(db: Session) -> dict:
    rows = db.query(ScoreWeight).all()
    if not rows:
        return DEFAULT_WEIGHTS
    return {r.dimension: r.weight for r in rows}


def _get_flag_thresholds(db: Session) -> dict:
    rows = db.query(FlagConfig).all()
    if not rows:
        return DEFAULT_FLAG_THRESHOLDS
    return {r.flag_key: r.threshold_value for r in rows}


def _jobs_for_entity(entity_type: str, entity_id: int, db: Session) -> list[Job]:
    if entity_type == "company":
        return db.query(Job).filter(Job.company_id == entity_id).all()
    return db.query(Job).filter(Job.qs_id == entity_id).all()


def _responses_for_jobs(job_ids: list[int], db: Session) -> list[QuestionResponse]:
    if not job_ids:
        return []
    return db.query(QuestionResponse).filter(QuestionResponse.job_id.in_(job_ids)).all()


def _weighted_avg(components: list[tuple[float, float]]) -> Optional[float]:
    """components = [(value, weight), ...]. Returns None if empty."""
    if not components:
        return None
    total_weight = sum(w for _, w in components)
    if total_weight == 0:
        return None
    return min(10.0, max(0.0, sum(v * w for v, w in components) / total_weight))


# ── Dimension calculators ──────────────────────────────────────────────────────

def calc_win_likelihood(jobs: list[Job], responses: list[QuestionResponse]) -> Optional[float]:
    components = []

    # Win rate (40%) – always calculable if jobs exist
    if jobs:
        won = sum(1 for j in jobs if j.status in WON_STATUSES)
        win_rate = (won / len(jobs)) * 10
        components.append((win_rate, 0.40))

    # Estimator gut feel (40%)
    gut_map = {"High": 10.0, "Medium": 5.0, "Low": 2.0}
    gut_vals = [
        gut_map[r.response_value]
        for r in responses
        if r.question_key == "gut_feeling" and r.response_value in gut_map
    ]
    if gut_vals:
        components.append((sum(gut_vals) / len(gut_vals), 0.40))

    # QS loyalty – did they give us work before? (20%)
    loyalty_map = {"Yes": 10.0, "First time": 6.0, "No": 2.0}
    loyalty_vals = [
        loyalty_map[r.response_value]
        for r in responses
        if r.question_key == "qs_gave_work_last_time" and r.response_value in loyalty_map
    ]
    if loyalty_vals:
        components.append((sum(loyalty_vals) / len(loyalty_vals), 0.20))

    return _weighted_avg(components)


def calc_relationship_quality(responses: list[QuestionResponse]) -> Optional[float]:
    components = []

    # QS responsiveness (25%)
    resp_vals = [
        float(r.response_value)
        for r in responses
        if r.question_key == "qs_responsiveness" and _is_numeric(r.response_value)
    ]
    if resp_vals:
        components.append((_scale_1_5_to_10(resp_vals), 0.25))

    # Documentation quality (25%)
    doc_vals = [
        float(r.response_value)
        for r in responses
        if r.question_key == "documentation_quality" and _is_numeric(r.response_value)
    ]
    if doc_vals:
        components.append((_scale_1_5_to_10(doc_vals), 0.25))

    # Sales relationship rating (25%)
    sales_vals = [
        float(r.response_value)
        for r in responses
        if r.question_key == "relationship_rating" and _is_numeric(r.response_value)
    ]
    if sales_vals:
        components.append((_scale_1_5_to_10(sales_vals), 0.25))

    # Repeat work indicator (25%)
    repeat_map = {"Yes": 10.0, "No": 1.0, "First time": 6.0}
    repeat_vals = [
        repeat_map[r.response_value]
        for r in responses
        if r.question_key == "worked_with_qs_before" and r.response_value in repeat_map
    ]
    if repeat_vals:
        components.append((sum(repeat_vals) / len(repeat_vals), 0.25))

    return _weighted_avg(components)


def calc_delivery_experience(responses: list[QuestionResponse]) -> Optional[float]:
    components = []

    # Coordination score (35%)
    coord_vals = [
        float(r.response_value)
        for r in responses
        if r.question_key == "client_coordination" and _is_numeric(r.response_value)
    ]
    if coord_vals:
        components.append((_scale_1_5_to_10(coord_vals), 0.35))

    # Variations fair (25%)
    var_map = {"Yes": 10.0, "No": 1.0, "Not applicable": 7.0}
    var_vals = [
        var_map[r.response_value]
        for r in responses
        if r.question_key == "variations_fair" and r.response_value in var_map
    ]
    if var_vals:
        components.append((sum(var_vals) / len(var_vals), 0.25))

    # Timeline respected (20%)
    time_map = {"Yes": 10.0, "No": 2.0}
    time_vals = [
        time_map[r.response_value]
        for r in responses
        if r.question_key == "timeline_respected" and r.response_value in time_map
    ]
    if time_vals:
        components.append((sum(time_vals) / len(time_vals), 0.20))

    # Work again (20%)
    again_map = {"Yes": 10.0, "Maybe": 5.0, "No": 1.0}
    again_vals = [
        again_map[r.response_value]
        for r in responses
        if r.question_key == "work_again" and r.response_value in again_map
    ]
    if again_vals:
        components.append((sum(again_vals) / len(again_vals), 0.20))

    return _weighted_avg(components)


def calc_payment_reliability(responses: list[QuestionResponse]) -> Optional[float]:
    components = []

    # Paid on time (35%)
    paid_map = {"Yes": 10.0, "Partially": 5.0, "No": 1.0}
    paid_vals = [
        paid_map[r.response_value]
        for r in responses
        if r.question_key == "paid_on_time" and r.response_value in paid_map
    ]
    if paid_vals:
        components.append((sum(paid_vals) / len(paid_vals), 0.35))

    # Days to payment – score: <=30=10, 31-60=6, 61-90=3, >90=1 (25%)
    day_vals = [
        _days_to_score(float(r.response_value))
        for r in responses
        if r.question_key == "days_to_payment" and _is_numeric(r.response_value)
    ]
    if day_vals:
        components.append((sum(day_vals) / len(day_vals), 0.25))

    # No disputes (25%)
    dispute_map = {"No": 10.0, "Yes": 1.0}
    dispute_vals = [
        dispute_map[r.response_value]
        for r in responses
        if r.question_key == "invoice_disputes" and r.response_value in dispute_map
    ]
    if dispute_vals:
        components.append((sum(dispute_vals) / len(dispute_vals), 0.25))

    # Collection difficulty (15%)
    diff_map = {"Easy": 10.0, "Some follow-up needed": 5.0, "Very difficult": 1.0}
    diff_vals = [
        diff_map[r.response_value]
        for r in responses
        if r.question_key == "collection_difficulty" and r.response_value in diff_map
    ]
    if diff_vals:
        components.append((sum(diff_vals) / len(diff_vals), 0.15))

    return _weighted_avg(components)


# ── Flag generators ────────────────────────────────────────────────────────────

def compute_flags(
    entity_type: str,
    entity_id: int,
    jobs: list[Job],
    scores: dict,
    thresholds: dict,
) -> list[str]:
    flags = []

    # Loss streak
    streak_threshold = int(thresholds.get("loss_streak_count", 3))
    sorted_jobs = sorted(jobs, key=lambda j: j.created_at or datetime.min, reverse=True)
    closed = [j for j in sorted_jobs if j.status in WON_STATUSES | LOST_STATUSES]
    if len(closed) >= streak_threshold:
        if all(j.status in LOST_STATUSES for j in closed[:streak_threshold]):
            flags.append("loss_streak")

    # Loyal
    loyal_threshold = thresholds.get("loyal_win_rate", 0.6)
    if len(jobs) >= 3:
        won = sum(1 for j in jobs if j.status in WON_STATUSES)
        if (won / len(jobs)) >= loyal_threshold:
            flags.append("loyal")

    # Payment risk
    pay_threshold = thresholds.get("payment_risk_threshold", 4.0)
    pay_score = scores.get("payment_reliability")
    if pay_score is not None and pay_score < pay_threshold:
        flags.append("payment_risk")

    # Gone cold
    cold_months = thresholds.get("cold_months", 6)
    cutoff = datetime.utcnow() - timedelta(days=30 * cold_months)
    recent = [j for j in jobs if j.created_at and j.created_at >= cutoff]
    if jobs and not recent:
        flags.append("gone_cold")

    return flags


# ── Main recalculation entry point ─────────────────────────────────────────────

def recalculate_scores(entity_type: str, entity_id: int, db: Session) -> dict:
    """
    Recalculate all dimension scores for a company or QS.
    Upserts into the scores table and returns the scores dict.
    """
    weights = _get_weights(db)
    thresholds = _get_flag_thresholds(db)

    jobs = _jobs_for_entity(entity_type, entity_id, db)
    job_ids = [j.id for j in jobs]
    responses = _responses_for_jobs(job_ids, db)

    dim_scores = {
        "win_likelihood":       calc_win_likelihood(jobs, responses),
        "relationship_quality": calc_relationship_quality(responses),
        "delivery_experience":  calc_delivery_experience(responses),
        "payment_reliability":  calc_payment_reliability(responses),
    }

    # Overall score (weighted avg of available dimensions)
    overall_components = [
        (v, weights.get(k, 0.25))
        for k, v in dim_scores.items()
        if v is not None
    ]
    dim_scores["overall_score"] = _weighted_avg(overall_components)

    # Upsert into DB
    now = datetime.utcnow()
    for dimension, score_val in dim_scores.items():
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
            existing.score = score_val
            existing.calculated_at = now
        else:
            db.add(Score(
                entity_type=entity_type,
                entity_id=entity_id,
                dimension=dimension,
                score=score_val,
                calculated_at=now,
            ))

    db.commit()

    flags = compute_flags(entity_type, entity_id, jobs, dim_scores, thresholds)
    return {"scores": dim_scores, "flags": flags}


def get_entity_scores(entity_type: str, entity_id: int, db: Session) -> dict:
    """Fetch persisted scores from DB without recalculating."""
    rows = (
        db.query(Score)
        .filter(Score.entity_type == entity_type, Score.entity_id == entity_id)
        .all()
    )
    scores = {r.dimension: r.score for r in rows}

    jobs = _jobs_for_entity(entity_type, entity_id, db)
    thresholds = _get_flag_thresholds(db)
    flags = compute_flags(entity_type, entity_id, jobs, scores, thresholds)
    return {"scores": scores, "flags": flags}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_numeric(val) -> bool:
    if val is None:
        return False
    try:
        float(val)
        return True
    except (ValueError, TypeError):
        return False


def _scale_1_5_to_10(vals: list[float]) -> float:
    avg = sum(vals) / len(vals)
    return ((avg - 1) / 4) * 10


def _days_to_score(days: float) -> float:
    if days <= 30:
        return 10.0
    if days <= 60:
        return 6.0
    if days <= 90:
        return 3.0
    return 1.0
