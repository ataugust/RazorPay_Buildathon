# ASC Agent Guide

Read `docs/phases/README.md` and the implemented phase documents in order before changing the project.

## Architectural invariant

Probabilistic components may parse, propose, select bounded strategies, and explain. Only deterministic Python code may calculate authoritative commercial values, enforce policy, approve offers, or authorize payment.

## Persistence invariant

ASC uses one persistence stack:

- SQLAlchemy models: `backend/app/db/models/`
- Session and engine: `backend/app/db/session.py`
- Configuration: `backend/app/core/config.py`
- Migrations: `backend/migrations/`
- Default database: `backend/data/asc.db`

Do not reintroduce the deprecated SQLModel database path or `backend/asc_database.db`.

