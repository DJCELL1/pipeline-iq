"""
Seed script for Pipeline IQ.
Run from inside backend/:
    python seed.py
Creates: 1 admin, 4 role users, 3 companies, 5 QS's, 10 jobs, responses, comments.
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, engine
from models import Base, User, UserRole, Company, QuantitySurveyor, Job, JobStatus, QuestionResponse, Comment
from auth_utils import hash_password
from scoring import recalculate_scores

Base.metadata.create_all(bind=engine)

db = SessionLocal()


def clear_all():
    db.query(Comment).delete()
    db.query(QuestionResponse).delete()
    db.query(Job).delete()
    db.query(QuantitySurveyor).delete()
    db.query(Company).delete()
    db.query(User).delete()
    db.commit()
    print("Cleared existing data.")


def seed():
    clear_all()

    # ── Users ──────────────────────────────────────────────────────────────────
    users = [
        User(name="Admin User",      email="admin@hardwaredirect.com.au",     password_hash=hash_password("admin123"),    role=UserRole.ADMIN),
        User(name="Alex Estimator",  email="alex@hardwaredirect.com.au",      password_hash=hash_password("pass123"),     role=UserRole.ESTIMATOR),
        User(name="Sam Sales",       email="sam@hardwaredirect.com.au",        password_hash=hash_password("pass123"),     role=UserRole.SALES),
        User(name="Pat PM",          email="pat@hardwaredirect.com.au",        password_hash=hash_password("pass123"),     role=UserRole.PROJECT_MANAGER),
        User(name="Casey AR",        email="casey@hardwaredirect.com.au",      password_hash=hash_password("pass123"),     role=UserRole.ACCOUNTS_RECEIVABLE),
    ]
    db.add_all(users)
    db.flush()

    admin_u, estimator_u, sales_u, pm_u, ar_u = users

    # ── Companies ──────────────────────────────────────────────────────────────
    buildco     = Company(name="BuildCo Constructions",  segment="Commercial")
    abc         = Company(name="ABC Developments",        segment="Residential")
    metro       = Company(name="Metro Builders Group",    segment="Industrial")

    db.add_all([buildco, abc, metro])
    db.flush()

    # ── Quantity Surveyors ─────────────────────────────────────────────────────
    qs1 = QuantitySurveyor(name="John Smith",    email="john@bcqs.com.au",    phone="0412 111 111", company_id=buildco.id)
    qs2 = QuantitySurveyor(name="Jane Doe",      email="jane@abcqs.com.au",   phone="0412 222 222", company_id=abc.id)
    qs3 = QuantitySurveyor(name="Mike Brown",    email="mike@metroqs.com.au", phone="0412 333 333", company_id=metro.id)
    qs4 = QuantitySurveyor(name="Sarah Wilson",  email="sarah@bcqs.com.au",   phone="0412 444 444", company_id=buildco.id)
    qs5 = QuantitySurveyor(name="Tom Davis",     email="tom@abcqs.com.au",    phone="0412 555 555", company_id=abc.id)

    db.add_all([qs1, qs2, qs3, qs4, qs5])
    db.flush()

    now = datetime.utcnow()

    # ── Jobs ───────────────────────────────────────────────────────────────────
    def d(days_ago):
        return now - timedelta(days=days_ago)

    jobs = [
        # BuildCo / John Smith – won jobs
        Job(job_number="HD-001", job_name="BuildCo Head Office Fitout",     company_id=buildco.id, qs_id=qs1.id, quote_value=285000, quote_date=d(180), status=JobStatus.COMPLETE),
        Job(job_number="HD-002", job_name="BuildCo Warehouse Extension",    company_id=buildco.id, qs_id=qs1.id, quote_value=142000, quote_date=d(120), status=JobStatus.INVOICED),
        Job(job_number="HD-003", job_name="BuildCo Retail Fit-Out Stage 2", company_id=buildco.id, qs_id=qs4.id, quote_value=95000,  quote_date=d(60),  status=JobStatus.IN_DELIVERY),

        # ABC / Jane Doe – mixed results
        Job(job_number="HD-004", job_name="ABC Apartments Block A",         company_id=abc.id,     qs_id=qs2.id, quote_value=410000, quote_date=d(200), status=JobStatus.LOST, loss_reason="Price"),
        Job(job_number="HD-005", job_name="ABC Apartments Block B",         company_id=abc.id,     qs_id=qs2.id, quote_value=390000, quote_date=d(150), status=JobStatus.WON),
        Job(job_number="HD-006", job_name="ABC Community Centre",           company_id=abc.id,     qs_id=qs5.id, quote_value=220000, quote_date=d(90),  status=JobStatus.LOST, loss_reason="Scope mismatch"),

        # Metro / Mike Brown – ongoing
        Job(job_number="HD-007", job_name="Metro Industrial Complex Stage 1", company_id=metro.id,  qs_id=qs3.id, quote_value=560000, quote_date=d(30),  status=JobStatus.PURSUING),
        Job(job_number="HD-008", job_name="Metro Logistics Hub",              company_id=metro.id,  qs_id=qs3.id, quote_value=320000, quote_date=d(300), status=JobStatus.LOST, loss_reason="Price"),

        # Mixed recent
        Job(job_number="HD-009", job_name="BuildCo Showroom Refit",          company_id=buildco.id, qs_id=qs4.id, quote_value=78000,  quote_date=d(10),  status=JobStatus.AT_QUOTE),
        Job(job_number="HD-010", job_name="ABC Townhouse Development",        company_id=abc.id,     qs_id=qs2.id, quote_value=185000, quote_date=d(5),   status=JobStatus.AT_QUOTE),
    ]

    db.add_all(jobs)
    db.flush()

    j001, j002, j003, j004, j005, j006, j007, j008, j009, j010 = jobs

    # ── Question Responses ─────────────────────────────────────────────────────
    def resp(job, user, role, key, val):
        return QuestionResponse(job_id=job.id, user_id=user.id, role=role, question_key=key, response_value=val)

    responses = [
        # HD-001 – Complete (all roles)
        resp(j001, estimator_u, "estimator", "qs_responsiveness", "5"),
        resp(j001, estimator_u, "estimator", "documentation_quality", "5"),
        resp(j001, estimator_u, "estimator", "tender_type", "Relationship"),
        resp(j001, estimator_u, "estimator", "gut_feeling", "High"),
        resp(j001, estimator_u, "estimator", "concerns", "No concerns"),
        resp(j001, estimator_u, "estimator", "worked_with_qs_before", "Yes"),
        resp(j001, estimator_u, "estimator", "qs_gave_work_last_time", "Yes"),
        resp(j001, estimator_u, "estimator", "notes", "Strong relationship with John"),
        resp(j001, sales_u, "sales", "negotiations", "Smooth"),
        resp(j001, sales_u, "sales", "scope_reduction_attempt", "No"),
        resp(j001, sales_u, "sales", "further_opportunity", "Yes"),
        resp(j001, sales_u, "sales", "relationship_rating", "5"),
        resp(j001, sales_u, "sales", "notes", "Client very happy with our service"),
        resp(j001, pm_u, "project_manager", "client_coordination", "5"),
        resp(j001, pm_u, "project_manager", "variations_fair", "Yes"),
        resp(j001, pm_u, "project_manager", "timeline_respected", "Yes"),
        resp(j001, pm_u, "project_manager", "documentation_issues", "None"),
        resp(j001, pm_u, "project_manager", "work_again", "Yes"),
        resp(j001, pm_u, "project_manager", "notes", "Great client to work with"),
        resp(j001, ar_u, "accounts_receivable", "paid_on_time", "Yes"),
        resp(j001, ar_u, "accounts_receivable", "days_to_payment", "21"),
        resp(j001, ar_u, "accounts_receivable", "invoice_disputes", "No"),
        resp(j001, ar_u, "accounts_receivable", "collection_difficulty", "Easy"),
        resp(j001, ar_u, "accounts_receivable", "account_concerns", "None"),

        # HD-002 – Invoiced
        resp(j002, estimator_u, "estimator", "qs_responsiveness", "4"),
        resp(j002, estimator_u, "estimator", "documentation_quality", "4"),
        resp(j002, estimator_u, "estimator", "tender_type", "Relationship"),
        resp(j002, estimator_u, "estimator", "gut_feeling", "High"),
        resp(j002, estimator_u, "estimator", "worked_with_qs_before", "Yes"),
        resp(j002, estimator_u, "estimator", "qs_gave_work_last_time", "Yes"),
        resp(j002, sales_u, "sales", "negotiations", "Some pushback"),
        resp(j002, sales_u, "sales", "scope_reduction_attempt", "Yes"),
        resp(j002, sales_u, "sales", "further_opportunity", "Yes"),
        resp(j002, sales_u, "sales", "relationship_rating", "4"),
        resp(j002, pm_u, "project_manager", "client_coordination", "4"),
        resp(j002, pm_u, "project_manager", "variations_fair", "Yes"),
        resp(j002, pm_u, "project_manager", "timeline_respected", "Yes"),
        resp(j002, pm_u, "project_manager", "work_again", "Yes"),
        resp(j002, ar_u, "accounts_receivable", "paid_on_time", "Yes"),
        resp(j002, ar_u, "accounts_receivable", "days_to_payment", "28"),
        resp(j002, ar_u, "accounts_receivable", "invoice_disputes", "No"),
        resp(j002, ar_u, "accounts_receivable", "collection_difficulty", "Easy"),

        # HD-003 – In Delivery
        resp(j003, estimator_u, "estimator", "qs_responsiveness", "4"),
        resp(j003, estimator_u, "estimator", "documentation_quality", "3"),
        resp(j003, estimator_u, "estimator", "tender_type", "Competitive"),
        resp(j003, estimator_u, "estimator", "gut_feeling", "Medium"),
        resp(j003, estimator_u, "estimator", "worked_with_qs_before", "Yes"),
        resp(j003, estimator_u, "estimator", "qs_gave_work_last_time", "Yes"),
        resp(j003, sales_u, "sales", "negotiations", "Some pushback"),
        resp(j003, sales_u, "sales", "scope_reduction_attempt", "No"),
        resp(j003, sales_u, "sales", "relationship_rating", "4"),
        resp(j003, pm_u, "project_manager", "client_coordination", "3"),
        resp(j003, pm_u, "project_manager", "variations_fair", "Yes"),
        resp(j003, pm_u, "project_manager", "timeline_respected", "Yes"),
        resp(j003, pm_u, "project_manager", "work_again", "Yes"),

        # HD-004 – Lost
        resp(j004, estimator_u, "estimator", "qs_responsiveness", "3"),
        resp(j004, estimator_u, "estimator", "documentation_quality", "3"),
        resp(j004, estimator_u, "estimator", "tender_type", "Competitive"),
        resp(j004, estimator_u, "estimator", "gut_feeling", "Low"),
        resp(j004, estimator_u, "estimator", "worked_with_qs_before", "Yes"),
        resp(j004, estimator_u, "estimator", "qs_gave_work_last_time", "No"),
        resp(j004, estimator_u, "estimator", "concerns", "Very competitive market, may not win on price"),

        # HD-005 – Won
        resp(j005, estimator_u, "estimator", "qs_responsiveness", "4"),
        resp(j005, estimator_u, "estimator", "documentation_quality", "4"),
        resp(j005, estimator_u, "estimator", "tender_type", "Competitive"),
        resp(j005, estimator_u, "estimator", "gut_feeling", "Medium"),
        resp(j005, estimator_u, "estimator", "worked_with_qs_before", "Yes"),
        resp(j005, estimator_u, "estimator", "qs_gave_work_last_time", "No"),
        resp(j005, sales_u, "sales", "negotiations", "Smooth"),
        resp(j005, sales_u, "sales", "scope_reduction_attempt", "No"),
        resp(j005, sales_u, "sales", "further_opportunity", "Maybe"),
        resp(j005, sales_u, "sales", "relationship_rating", "3"),

        # HD-006 – Lost
        resp(j006, estimator_u, "estimator", "qs_responsiveness", "2"),
        resp(j006, estimator_u, "estimator", "documentation_quality", "2"),
        resp(j006, estimator_u, "estimator", "tender_type", "Competitive"),
        resp(j006, estimator_u, "estimator", "gut_feeling", "Low"),
        resp(j006, estimator_u, "estimator", "worked_with_qs_before", "No"),
        resp(j006, estimator_u, "estimator", "concerns", "Documentation was late and incomplete"),

        # HD-007 – Pursuing (estimator only)
        resp(j007, estimator_u, "estimator", "qs_responsiveness", "3"),
        resp(j007, estimator_u, "estimator", "documentation_quality", "3"),
        resp(j007, estimator_u, "estimator", "tender_type", "Competitive"),
        resp(j007, estimator_u, "estimator", "gut_feeling", "Medium"),
        resp(j007, estimator_u, "estimator", "worked_with_qs_before", "Yes"),
        resp(j007, estimator_u, "estimator", "qs_gave_work_last_time", "First time"),
        resp(j007, estimator_u, "estimator", "concerns", "Large job, margin will be tight"),

        # HD-008 – Lost
        resp(j008, estimator_u, "estimator", "qs_responsiveness", "2"),
        resp(j008, estimator_u, "estimator", "documentation_quality", "2"),
        resp(j008, estimator_u, "estimator", "tender_type", "Competitive"),
        resp(j008, estimator_u, "estimator", "gut_feeling", "Low"),
        resp(j008, estimator_u, "estimator", "worked_with_qs_before", "Yes"),
        resp(j008, estimator_u, "estimator", "qs_gave_work_last_time", "No"),

        # HD-009 & HD-010 – At Quote, no responses yet
    ]

    db.add_all(responses)
    db.flush()

    # ── Comments ───────────────────────────────────────────────────────────────
    comments = [
        Comment(entity_type="company", entity_id=buildco.id,  user_id=sales_u.id,     body="BuildCo is our strongest relationship. Always responsive and fair."),
        Comment(entity_type="company", entity_id=buildco.id,  user_id=pm_u.id,         body="On-site team is excellent, easy to coordinate with."),
        Comment(entity_type="company", entity_id=abc.id,       user_id=estimator_u.id, body="ABC is getting more competitive lately, pricing pressure has increased."),
        Comment(entity_type="company", entity_id=metro.id,     user_id=estimator_u.id, body="Metro is hard to win with. Their QS shops around aggressively."),
        Comment(entity_type="qs",      entity_id=qs1.id,       user_id=estimator_u.id, body="John Smith is one of the best QS's we work with. Very clear documentation."),
        Comment(entity_type="qs",      entity_id=qs2.id,       user_id=estimator_u.id, body="Jane Doe tends to go to price. Need a strong relationship approach."),
        Comment(entity_type="qs",      entity_id=qs3.id,       user_id=sales_u.id,     body="Mike Brown is very price-focused. Hard to compete unless we're cheapest."),
        Comment(entity_type="job",     entity_id=j007.id,      user_id=estimator_u.id, body="This is a big one - worth chasing hard. Metro are looking to expand."),
        Comment(entity_type="job",     entity_id=j005.id,      user_id=sales_u.id,     body="Negotiations went smoother than expected for a competitive tender."),
    ]

    db.add_all(comments)
    db.commit()

    print(f"Users created: {len(users)}")
    print(f"Companies created: 3")
    print(f"QS's created: 5")
    print(f"Jobs created: 10")
    print(f"Responses created: {len(responses)}")
    print(f"Comments created: {len(comments)}")

    # Recalculate scores for all entities
    print("\nRecalculating scores...")
    for company in [buildco, abc, metro]:
        result = recalculate_scores("company", company.id, db)
        print(f"  {company.name}: overall={result['scores'].get('overall_score')}, flags={result['flags']}")

    for qs in [qs1, qs2, qs3, qs4, qs5]:
        result = recalculate_scores("qs", qs.id, db)
        print(f"  {qs.name}: overall={result['scores'].get('overall_score')}, flags={result['flags']}")

    print("\nSeed complete!")
    print("\nLogin credentials:")
    print("  Admin:    admin@hardwaredirect.com.au / admin123")
    print("  Estimator: alex@hardwaredirect.com.au / pass123")
    print("  Sales:    sam@hardwaredirect.com.au / pass123")
    print("  PM:       pat@hardwaredirect.com.au / pass123")
    print("  AR:       casey@hardwaredirect.com.au / pass123")


if __name__ == "__main__":
    seed()
    db.close()
