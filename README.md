# Pipeline IQ

**Customer Intelligence Platform for Hardware Direct**

Predict which companies and QS's are worth pursuing by capturing cross-team insights and turning them into living intelligence scores.

---

## Quick Start (Docker)

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY to a long random string

# 2. Start all services
docker-compose up -d

# 3. Seed the database with sample data
docker-compose exec backend python seed.py

# 4. Open the app
#    Frontend:  http://localhost:8501
#    API docs:  http://localhost:8000/docs
```

---

## Manual / Local Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ (or Railway)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure env
cp ../.env.example ../.env
# Edit DATABASE_URL and SECRET_KEY

# Run DB migrations
alembic upgrade head

# Seed sample data
python seed.py

# Start API server
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start Streamlit
streamlit run app.py
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://pipelineiq:pipelineiq_secret@localhost:5432/pipelineiq` |
| `SECRET_KEY` | JWT signing secret (change in production!) | `change-me-in-production` |
| `ACCESS_TOKEN_EXPIRE_HOURS` | Token lifetime in hours | `8` |
| `BACKEND_URL` | URL of the FastAPI backend (used by Streamlit) | `http://localhost:8000` |

---

## Seed Credentials

After running `python seed.py`:

| Role | Email | Password |
|---|---|---|
| Admin | admin@hardwaredirect.com.au | admin123 |
| Estimator | alex@hardwaredirect.com.au | pass123 |
| Sales | sam@hardwaredirect.com.au | pass123 |
| Project Manager | pat@hardwaredirect.com.au | pass123 |
| Accounts Receivable | casey@hardwaredirect.com.au | pass123 |

---

## Architecture

```
Browser (Streamlit :8501)
    │  HTTP
    ▼
FastAPI Backend (:8000)
    │  SQLAlchemy
    ▼
PostgreSQL
```

All database access goes through FastAPI. Streamlit never queries the DB directly.

### Backend (`backend/`)
| File | Purpose |
|---|---|
| `main.py` | FastAPI app, CORS, router registration |
| `models.py` | SQLAlchemy ORM models |
| `schemas.py` | Pydantic request/response schemas |
| `scoring.py` | Scoring engine — calculates all 4 dimensions + flags |
| `database.py` | DB session factory |
| `auth_utils.py` | JWT creation/validation, password hashing |
| `routes/auth.py` | Login endpoint |
| `routes/companies.py` | Company CRUD + score enrichment |
| `routes/qs.py` | QS CRUD + leaderboard |
| `routes/jobs.py` | Job CRUD, CSV import, analytics endpoints |
| `routes/responses.py` | Question response submission + validation |
| `routes/comments.py` | Comment CRUD |
| `routes/scores.py` | Score retrieval, recalculation, weight/flag config |
| `routes/admin.py` | User management |
| `alembic/` | DB migrations |
| `seed.py` | Sample data seed script |

### Frontend (`frontend/`)
| File | Purpose |
|---|---|
| `app.py` | Streamlit entry point, auth gate, sidebar nav, routing |
| `utils/api_client.py` | All FastAPI HTTP calls centralised here |
| `utils/auth.py` | Session state auth helpers |
| `pages/home.py` | My Actions — pending question sets |
| `pages/overview.py` | Dashboard — KPIs and charts |
| `pages/companies.py` | Company list |
| `pages/company_detail.py` | Company profile with score gauges |
| `pages/qs_intelligence.py` | QS list + detail view |
| `pages/qs_leaderboard.py` | Ranked QS table |
| `pages/loss_analysis.py` | Loss reason charts |
| `pages/job_log.py` | Job list + detail + question forms |
| `pages/upload.py` | CSV import with column mapping |
| `pages/admin.py` | User mgmt, score weights, flag config |

---

## Scoring Engine

Four dimensions are calculated per Company and per QS from question responses:

| Dimension | Inputs | Weight (default) |
|---|---|---|
| Win Likelihood | Estimator gut feel, historical win rate, QS loyalty | 25% |
| Relationship Quality | QS responsiveness, documentation quality, sales rating, repeat work | 30% |
| Delivery Experience | PM coordination, variations fairness, timeline respect, work again | 25% |
| Payment Reliability | AR paid on time, days to payment, disputes, collection difficulty | 20% |

**Overall Score** = weighted average of available dimensions (0–10).

Scores are recalculated automatically after every response submission, job status change, or CSV import. Admins can also trigger a full recalculation from the Admin panel.

### Flags

| Flag | Trigger |
|---|---|
| 🟢 Loyal | Win rate ≥ 60% with 3+ jobs |
| 🔴 Loss Streak | Last 3 closed jobs are all losses |
| 🟠 Payment Risk | Payment Reliability score < 4.0 |
| 🔵 Gone Cold | No job activity in last 6 months |

All thresholds are configurable in Admin → Flag Thresholds.

---

## CSV Import Format

Upload from Upload Jobs page. Auto-detects common header names.

| Field | Required | Notes |
|---|---|---|
| Job Number | ✅ | Must be unique. Duplicates skipped. |
| Job Name | ✅ | |
| Company Name | — | Auto-creates company if not found |
| QS Name | — | Auto-creates QS if not found |
| Quote Value | — | Numeric, strips $ and commas |
| Quote Date | — | dd/mm/yyyy or ISO format |
| Status | — | e.g. "Won", "Lost", "At Quote" |

---

## Railway Deployment

1. Create a PostgreSQL database on Railway.
2. Copy the connection string into `DATABASE_URL`.
3. Deploy the `backend/` directory as a Python service.
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Deploy the `frontend/` directory as a separate Python service.
   - Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
   - Set `BACKEND_URL` to the Railway backend service URL.
5. Run migrations: `alembic upgrade head`
6. Run seed: `python seed.py`
