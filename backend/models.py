import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text,
    Enum as SAEnum, Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class UserRole(str, enum.Enum):
    ESTIMATOR = "estimator"
    SALES = "sales"
    PROJECT_MANAGER = "project_manager"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    ADMIN = "admin"


class JobStatus(str, enum.Enum):
    AT_QUOTE = "at_quote"
    PURSUING = "pursuing"
    WON = "won"
    LOST = "lost"
    IN_DELIVERY = "in_delivery"
    INVOICED = "invoiced"
    COMPLETE = "complete"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    responses = relationship("QuestionResponse", back_populates="user")
    comments = relationship("Comment", back_populates="user")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    segment = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    quantity_surveyors = relationship("QuantitySurveyor", back_populates="company")
    jobs = relationship("Job", back_populates="company")


class QuantitySurveyor(Base):
    __tablename__ = "quantity_surveyors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255))
    phone = Column(String(50))
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="quantity_surveyors")
    jobs = relationship("Job", back_populates="qs")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_number = Column(String(100), unique=True, nullable=False, index=True)
    job_name = Column(String(500), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    qs_id = Column(Integer, ForeignKey("quantity_surveyors.id"), nullable=True)
    quote_value = Column(Float, nullable=True)
    quote_date = Column(DateTime, nullable=True)
    status = Column(SAEnum(JobStatus), default=JobStatus.AT_QUOTE, nullable=False)
    loss_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="jobs")
    qs = relationship("QuantitySurveyor", back_populates="jobs")
    responses = relationship("QuestionResponse", back_populates="job", cascade="all, delete-orphan")


class QuestionResponse(Base):
    __tablename__ = "question_responses"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(50), nullable=False)
    question_key = Column(String(100), nullable=False)
    response_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="responses")
    user = relationship("User", back_populates="responses")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False)   # 'company', 'qs', 'job'
    entity_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="comments")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False)   # 'company', 'qs'
    entity_id = Column(Integer, nullable=False, index=True)
    dimension = Column(String(100), nullable=False)
    score = Column(Float, nullable=True)
    calculated_at = Column(DateTime, default=datetime.utcnow)


# Score weights config (stored in DB so Admin can change them)
class ScoreWeight(Base):
    __tablename__ = "score_weights"

    id = Column(Integer, primary_key=True)
    dimension = Column(String(100), unique=True, nullable=False)
    weight = Column(Float, nullable=False, default=0.25)
    updated_at = Column(DateTime, default=datetime.utcnow)


# Flag threshold config
class FlagConfig(Base):
    __tablename__ = "flag_configs"

    id = Column(Integer, primary_key=True)
    flag_key = Column(String(100), unique=True, nullable=False)
    threshold_value = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
