from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import purchase, audit, commerce, buyer, access
from app.db.bootstrap import bootstrap_database


def recover_interrupted_buyer_drafts():
    """Turn abandoned background work into an explicit, retryable state."""
    from app.db.session import SessionLocal
    from app.db.models.buyer_draft import BuyerDraft
    from sqlalchemy import select
    with SessionLocal() as db:
        drafts = db.scalars(select(BuyerDraft).where(BuyerDraft.state.in_(["PREPARING", "SENT", "WAITING"]))).all()
        for draft in drafts:
            draft.state = "ERROR"
            draft.data = {**draft.data, "error": "The server restarted while processing this request. Your saved requirements can be reviewed and retried."}
        db.commit()
    return len(drafts)


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap_database()
    access.passcode()
    recover_interrupted_buyer_drafts()
    yield

app = FastAPI(
    title="ASC — Autonomous Sales Counterparty API",
    description="Merchant-side autonomous AI commerce system with deterministic Control Plane.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(access.MerchantBoundary)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    requested_provider = os.getenv("ASC_LLM_PROVIDER", "deterministic").strip().lower()
    gemini_configured = requested_provider == "gemini" and bool(os.getenv("GEMINI_API_KEY", "").strip())
    return {
        "status": "healthy",
        "service": "ASC Autonomous Sales Counterparty Backend",
        "version": "1.0.0",
        "agent_provider": "gemini" if gemini_configured else "deterministic",
        "agent_model": os.getenv("ASC_LLM_MODEL", "gemini-3.5-flash") if gemini_configured else None,
        "agent_configured": gemini_configured or requested_provider == "deterministic",
    }

app.include_router(purchase.router)
app.include_router(audit.router)
app.include_router(commerce.router)
app.include_router(buyer.router)
app.include_router(access.router)
