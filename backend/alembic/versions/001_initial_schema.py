"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("segment", sa.String(255)),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table(
        "quantity_surveyors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id")),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_number", sa.String(100), unique=True, nullable=False),
        sa.Column("job_name", sa.String(500), nullable=False),
        sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id")),
        sa.Column("qs_id", sa.Integer, sa.ForeignKey("quantity_surveyors.id")),
        sa.Column("quote_value", sa.Float),
        sa.Column("quote_date", sa.DateTime),
        sa.Column("status", sa.String(50), nullable=False, server_default="at_quote"),
        sa.Column("loss_reason", sa.Text),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table(
        "question_responses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("question_key", sa.String(100), nullable=False),
        sa.Column("response_value", sa.Text),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table(
        "scores",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("dimension", sa.String(100), nullable=False),
        sa.Column("score", sa.Float),
        sa.Column("calculated_at", sa.DateTime),
    )
    op.create_table(
        "score_weights",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dimension", sa.String(100), unique=True, nullable=False),
        sa.Column("weight", sa.Float, nullable=False),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_table(
        "flag_configs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("flag_key", sa.String(100), unique=True, nullable=False),
        sa.Column("threshold_value", sa.Float, nullable=False),
        sa.Column("updated_at", sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table("flag_configs")
    op.drop_table("score_weights")
    op.drop_table("scores")
    op.drop_table("comments")
    op.drop_table("question_responses")
    op.drop_table("jobs")
    op.drop_table("quantity_surveyors")
    op.drop_table("companies")
    op.drop_table("users")
