# Phase 3 — Commerce Control Plane

## Status

Implemented and integration-tested on 2026-09-04.

## Invariant

> ASC proposes. The Control Plane decides.

An offer is approved only when all six gates pass:

1. Margin
2. Inventory
3. Budget
4. Discount
5. Specification
6. Mandate

## Authoritative files

- `backend/app/control_plane/control_plane_engine.py`
- `backend/app/control_plane/*_gate.py`
- `backend/app/control_plane/gate_result.py`
- `backend/app/audit/audit_service.py`
- `backend/app/api/audit.py`

The Control Plane and the public audit endpoint now use the same `SessionLocal`, SQLAlchemy `AuditEvent` model, and database. The endpoint returns chronological events with `metadata` mapped from the database `metadata_json` column.

## Validation

- `python -m scripts.test_phase3` verified a specification rejection and a valid six-gate approval with eight persisted events.
- `python -m scripts.test_phase1_3_integration` verified purchase-to-audit retrieval through the public FastAPI endpoints.

