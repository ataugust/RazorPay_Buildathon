# Phase 1 — Foundation

## Status

Complete and consolidated on 2026-09-04.

## Responsibilities

- FastAPI application and health endpoint
- Pydantic API schemas
- SQLAlchemy engine, sessions, and models
- Alembic-managed schema
- Idempotent product and merchant-policy seeds
- Next.js frontend foundation

## Authoritative files

- `backend/app/main.py` — lifespan startup
- `backend/app/db/bootstrap.py` — migrations and seeds
- `backend/app/db/session.py` — engine and `SessionLocal`
- `backend/app/db/models/` — database tables
- `backend/app/domain/schemas.py` — HTTP/domain input schemas
- `backend/migrations/` — schema history
- `backend/data/asc.db` — default database

Startup calls `bootstrap_database()`, upgrades Alembic to `head`, then idempotently seeds products and policies. The former SQLModel modules are compatibility-only and no longer create or query a separate database.

## Validation

`python -m scripts.test_phase1_3_integration` creates a temporary database, runs migrations and seeds, calls the health and purchase APIs, and verifies audit retrieval.

