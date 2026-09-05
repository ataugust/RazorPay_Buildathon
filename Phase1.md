# Phase 1 — Foundation

## Purpose

Establish the runnable vertical slice: repository structure, FastAPI, Next.js, SQLite, inventory, request schemas, migrations, and API entry points.

## Status

**Implemented, with persistence integration debt.** The active offer pipeline uses SQLAlchemy and `backend/data/asc.db`; FastAPI startup and the public audit reader still use a legacy SQLModel path.

## Implemented surface

- `GET /api/health`
- `POST /api/purchase/request` for structured `BuyerRequest`
- `POST /api/purchase/prompt` for deterministic prompt parsing
- `GET /api/audit/transaction/{transaction_id}`
- Next.js frontend under `frontend/src/app`
- Alembic migrations `001 -> 002 -> 003`
- Product and merchant-policy seed scripts

## Source map

| Concern | Source |
| --- | --- |
| FastAPI app | `backend/app/main.py` |
| Purchase API | `backend/app/api/purchase.py` |
| Public schemas | `backend/app/domain/models.py` |
| Active DB session | `backend/app/db/session.py` |
| Active DB URL | `backend/app/core/config.py` |
| SQLAlchemy models | `backend/app/db/models/` |
| Migrations | `backend/migrations/versions/` |
| Seeds | `backend/scripts/seed_products.py`, `seed_policy.py` |

## BuyerRequest contract

```json
{
  "request_id": "REQ-001",
  "items": [{"product_query": "Lenovo IdeaPad", "quantity": 20}],
  "max_budget_paise": 240000000,
  "currency": "INR",
  "max_delivery_days": 7,
  "preferences": [],
  "mandate_id": "MANDATE-DEMO-001"
}
```

## Critical persistence split

Current Phase 2/3 path:

- `app.db.models.*`
- `app.db.session.SessionLocal`
- `app.core.config.DATABASE_URL`
- `backend/data/asc.db`

Legacy path:

- SQLModel tables in `app/domain/models.py`
- `app.db.database`
- `app.db.seed`
- `backend/asc_database.db`

`app/main.py` currently initializes and seeds the legacy path, not necessarily the database used by `ASCOrchestrator`.

## Verification

- Structure, migrations, seeds, schemas: inspected.
- Active DB contents: 10 products, 1 policy, 135 audit events.
- Python syntax: passed.
- Runtime suite: not rerun because the committed virtual environment is not portable.

## Clean completion criteria

- One persistence stack is used by startup, APIs, orchestration, and tests.
- A fresh environment can migrate and seed successfully.
- Health and structured purchase endpoints pass smoke tests.

