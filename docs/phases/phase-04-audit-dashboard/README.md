# Phase 4 — Audit Trail and Operations Dashboard

## Status

Implemented and integration-tested on 2026-09-04.

## Purpose

Make autonomous commerce observable. Operators can see the buyer intent,
candidate strategy, six deterministic gate decisions, final verdict, and
chronological audit evidence without inspecting server logs or SQLite directly.

## Backend capabilities

| Endpoint | Purpose |
| --- | --- |
| `GET /api/audit/transaction/{id}` | Complete chronological audit history for one transaction |
| `GET /api/audit/transaction/{id}/stream` | Server-sent event stream for one transaction |
| `GET /api/audit/recent?limit=50` | Recent persisted events for operational views |
| `GET /api/audit/summary` | Real transaction and gate counts derived from persisted events |

The stream replays existing events in database order, continues polling while a
transaction is active, and sends a terminal `complete` event after
`CANDIDATE_APPROVED` or `CANDIDATE_REJECTED`. It sends keep-alive comments while
waiting and closes after an idle timeout.

## Frontend capabilities

- Dual-pane negotiation and deterministic Control Plane workspace
- Trust-boundary visualization between proposal and approval surfaces
- Six-gate result table with expected, actual, status, reason, and metadata
- Live audit feed backed by `EventSource`
- Visible waiting, connecting, live, complete, and snapshot states
- Transaction-history snapshot fallback when SSE is unavailable
- Offline scenario fallback when the backend itself is unavailable
- Audit filters for all, gate, pass, and fail events
- Localized audit timestamps and accessible live updates

## Authoritative files

- `backend/app/api/audit.py`
- `backend/app/audit/audit_service.py`
- `frontend/src/app/page.tsx`
- `frontend/src/types/index.ts`
- `backend/scripts/test_phase1_3_integration.py`

## Event contract

```json
{
  "id": 42,
  "timestamp": "2026-09-04T18:51:43+00:00",
  "transaction_id": "TXN-1234ABCD",
  "component": "MARGIN_GATE",
  "event_type": "GATE_CHECK_PASS",
  "status": "PASS",
  "message": "Deterministic explanation",
  "metadata": {}
}
```

SSE frames use `event: audit`; terminal frames use `event: complete`.

## Verification

- Backend integration test passed against a clean temporary database.
- The test verifies migrations, seeds, purchase execution, six gates, persisted
  audit retrieval, summary, recent events, SSE audit frames, and the terminal
  completion frame.
- The Next.js production build completed successfully with TypeScript and lint
  checks.
- Backend and frontend local health requests both returned HTTP 200.

## Phase boundary

Phase 4 observes and explains deterministic behavior. It does not introduce an
LLM, stateful buyer/merchant negotiation, or real payment execution; those
belong to later phases.

