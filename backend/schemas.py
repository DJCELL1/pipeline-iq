from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel

from models import UserRole, JobStatus


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


# ── Users ─────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    name: str
    email: str
    role: UserRole


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Companies ─────────────────────────────────────────────────────────────────

class CompanyBase(BaseModel):
    name: str
    segment: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    segment: Optional[str] = None


class CompanyOut(CompanyBase):
    id: int
    created_at: datetime
    scores: Optional[dict] = None
    flags: Optional[List[str]] = None

    class Config:
        from_attributes = True


# ── Quantity Surveyors ────────────────────────────────────────────────────────

class QSBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company_id: Optional[int] = None


class QSCreate(QSBase):
    pass


class QSUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_id: Optional[int] = None


class QSOut(QSBase):
    id: int
    created_at: datetime
    company_name: Optional[str] = None
    scores: Optional[dict] = None
    flags: Optional[List[str]] = None

    class Config:
        from_attributes = True


# ── Jobs ──────────────────────────────────────────────────────────────────────

class JobBase(BaseModel):
    job_number: str
    job_name: str
    company_id: Optional[int] = None
    qs_id: Optional[int] = None
    quote_value: Optional[float] = None
    quote_date: Optional[datetime] = None
    status: JobStatus = JobStatus.AT_QUOTE
    loss_reason: Optional[str] = None


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    job_name: Optional[str] = None
    company_id: Optional[int] = None
    qs_id: Optional[int] = None
    quote_value: Optional[float] = None
    quote_date: Optional[datetime] = None
    status: Optional[JobStatus] = None
    loss_reason: Optional[str] = None


class JobOut(JobBase):
    id: int
    created_at: datetime
    company_name: Optional[str] = None
    qs_name: Optional[str] = None

    class Config:
        from_attributes = True


class JobImportRow(BaseModel):
    job_number: str
    job_name: str
    company_name: Optional[str] = None
    qs_name: Optional[str] = None
    quote_value: Optional[float] = None
    quote_date: Optional[str] = None
    status: Optional[str] = None


# ── Question Responses ────────────────────────────────────────────────────────

class ResponseCreate(BaseModel):
    job_id: int
    question_key: str
    response_value: Optional[str] = None


class ResponseBulkCreate(BaseModel):
    job_id: int
    responses: List[dict]   # [{question_key, response_value}]


class ResponseOut(BaseModel):
    id: int
    job_id: int
    user_id: int
    user_name: Optional[str] = None
    role: str
    question_key: str
    response_value: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Comments ──────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    entity_type: str
    entity_id: int
    body: str


class CommentOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    user_id: int
    user_name: Optional[str] = None
    role: Optional[str] = None
    body: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Scores ────────────────────────────────────────────────────────────────────

class ScoreOut(BaseModel):
    entity_type: str
    entity_id: int
    dimension: str
    score: Optional[float]
    calculated_at: datetime

    class Config:
        from_attributes = True


class EntityScores(BaseModel):
    entity_type: str
    entity_id: int
    win_likelihood: Optional[float] = None
    relationship_quality: Optional[float] = None
    delivery_experience: Optional[float] = None
    payment_reliability: Optional[float] = None
    overall_score: Optional[float] = None
    flags: List[str] = []


# ── Score Weights ─────────────────────────────────────────────────────────────

class ScoreWeightUpdate(BaseModel):
    win_likelihood: float = 0.25
    relationship_quality: float = 0.30
    delivery_experience: float = 0.25
    payment_reliability: float = 0.20


class FlagConfigUpdate(BaseModel):
    payment_risk_threshold: float = 4.0
    cold_months: float = 6.0
    loss_streak_count: float = 3.0
    loyal_win_rate: float = 0.6


# ── Dashboard / Analytics ─────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_pipeline_value: float
    win_rate: float
    jobs_this_month: int
    active_jobs: int
    total_companies: int
    total_qs: int
