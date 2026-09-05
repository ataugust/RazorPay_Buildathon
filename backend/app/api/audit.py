import asyncio
import json
from datetime import timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.audit.audit_service import AuditService
from app.db.models.audit_event import AuditEvent
from app.db.session import SessionLocal, get_db

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"])


def serialize_event(event: AuditEvent) -> Dict[str, Any]:
    timestamp = event.timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return {
        "id": event.id,
        "timestamp": timestamp.isoformat(),
        "transaction_id": event.transaction_id,
        "component": event.component,
        "event_type": event.event_type,
        "status": event.status,
        "message": event.message,
        "metadata": event.metadata_json or {},
    }


@router.get("/summary")
def get_audit_summary(db: Session = Depends(get_db)):
    """Returns real operational counts derived from persisted audit events."""
    return AuditService.get_operational_summary(db)


@router.get("/recent")
def get_recent_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Returns the newest persisted events for operational dashboards."""
    return {"events": [serialize_event(event) for event in AuditService.get_recent_events(db, limit)]}

@router.get("/transaction/{transaction_id}")
def get_transaction_audit_trail(
    transaction_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves chronological audit events for a transaction."""
    events = AuditService.get_transaction_audit_trail(db, transaction_id)
    return {
        "transaction_id": transaction_id,
        "events": [serialize_event(event) for event in events],
    }


@router.get("/transaction/{transaction_id}/stream")
def stream_transaction_audit(transaction_id: str):
    """Streams persisted transaction events as server-sent events.

    Existing events are replayed in order. The stream stays open while a
    transaction is active and emits a terminal ``complete`` event after the
    Control Plane records its final verdict.
    """

    async def event_stream():
        last_id = 0
        idle_cycles = 0

        while idle_cycles < 80:
            with SessionLocal() as db:
                events = AuditService.get_transaction_events_after(
                    db, transaction_id, last_id
                )

            if not events:
                idle_cycles += 1
                yield ": keep-alive\n\n"
                await asyncio.sleep(0.25)
                continue

            idle_cycles = 0
            for event in events:
                last_id = event.id or last_id
                payload = json.dumps(serialize_event(event))
                yield f"id: {last_id}\nevent: audit\ndata: {payload}\n\n"

                if event.event_type in {
                    "CANDIDATE_APPROVED",
                    "CANDIDATE_REJECTED",
                }:
                    yield "event: complete\ndata: {}\n\n"
                    return

        yield "event: timeout\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
