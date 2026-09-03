from fastapi import APIRouter
from app.audit.service import AuditService

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"])

@router.get("/transaction/{transaction_id}")
def get_transaction_audit_trail(transaction_id: str):
    """Retrieves chronological audit events for a transaction."""
    events = AuditService.get_events_for_transaction(transaction_id)
    return {"transaction_id": transaction_id, "events": events}
