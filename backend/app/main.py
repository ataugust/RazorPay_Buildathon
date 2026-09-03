from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import init_db
from app.db.seed import seed_data
from app.api import purchase, audit

app = FastAPI(
    title="ASC — Autonomous Sales Counterparty API",
    description="Merchant-side autonomous AI commerce system with deterministic Control Plane.",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()
    seed_data()

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ASC Autonomous Sales Counterparty Backend",
        "version": "1.0.0"
    }

app.include_router(purchase.router)
app.include_router(audit.router)
