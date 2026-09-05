# Phase 3 — Commerce Control Plane

## Purpose

Provide the deterministic authorization boundary for candidate offers.

> ASC proposes. The Control Plane decides.

## Status

**Gate engine and audit writes are implemented; end-to-end audit retrieval is not complete.**

## Flow

```text
Winning candidate
→ EVALUATION_START audit event
→ MarginGate
→ InventoryGate
→ BudgetGate
→ DiscountGate
→ SpecificationGate
→ MandateGate
→ APPROVED only if every gate passes
→ final verdict audit event
```

## Source map

| Concern | Source |
| --- | --- |
| Engine | `backend/app/control_plane/control_plane_engine.py` |
| Gate result | `backend/app/control_plane/gate_result.py` |
| Gate implementations | `backend/app/control_plane/*_gate.py` |
| Active audit writer | `backend/app/audit/audit_service.py` |
| Public audit route | `backend/app/api/audit.py` |
| Legacy audit reader | `backend/app/audit/service.py` |
| Verification | `backend/scripts/test_phase3.py` |

## GateResult contract

```json
{
  "gate": "MARGIN_GATE",
  "status": "PASS",
  "expected": ">= 15.0%",
  "actual": "16.67%",
  "reason": "Deterministic explanation",
  "metadata": {}
}
```

## Gates

- **MarginGate:** margin is at or above merchant minimum.
- **InventoryGate:** every SKU exists and requested quantity is available.
- **BudgetGate:** total is within buyer budget.
- **DiscountGate:** discount is within policy ceiling.
- **SpecificationGate:** laptop RAM, storage, and CPU satisfy hard constraints.
- **MandateGate:** total, category, and expiry satisfy buyer authorization.

## Audit behavior

The Control Plane writes evaluation start, each gate result, and the final verdict through SQLAlchemy into `backend/data/asc.db`.

## Critical API gap

The public audit route imports `app.audit.service`, which reads the legacy SQLModel database. The Control Plane writes through `app.audit.audit_service` into the SQLAlchemy database. Therefore `/api/audit/transaction/{id}` may not return the events just written by a purchase transaction. The frontend fallback data can mask this problem.

## Additional safety gaps

- Missing mandates pass with a default authorization assumption.
- Malformed mandate expiration values are silently ignored.
- The orchestrator supplies fixed hardware requirements and a generated demo mandate instead of deriving validated values from the request.
- Gate statuses are unconstrained strings.

## Verification

- Six-gate registration and all-pass aggregation: inspected.
- Audit write records: present in the active DB; 135 events observed.
- Python syntax: passed.
- Runtime Phase 3 script: not rerun due to the nonportable virtual environment.
- Public transaction-to-audit API integration: not verified and expected to fail consistency because of the database split.

## Required before Phase 4

1. Make the audit route use `SessionLocal` and `app.audit.audit_service.AuditService`.
2. Consolidate startup, migrations, seeds, orchestration, and audit reads onto one database.
3. Define fail-closed rules for missing or malformed mandates.
4. Move specifications and mandate data into validated request contracts.
5. Add pass/fail tests for every gate.
6. Add an API integration test that submits a purchase and retrieves the same transaction's audit trail.

