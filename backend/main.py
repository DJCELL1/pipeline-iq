import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import engine
from models import Base
from routes import auth, companies, qs, jobs, responses, comments, scores, admin

# Create tables on startup (Alembic handles migrations in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Pipeline IQ API",
    description="Customer Intelligence Platform for Hardware Direct",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(qs.router)
app.include_router(jobs.router)
app.include_router(responses.router)
app.include_router(comments.router)
app.include_router(scores.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "Pipeline IQ API"}
