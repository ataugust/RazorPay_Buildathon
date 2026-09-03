from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models.audit_event import AuditEvent

class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        transaction_id: str,
        component: str,
        event_type: str,
        status: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        event = AuditEvent(
            transaction_id=transaction_id,
            timestamp=datetime.now(timezone.utc),
            component=component,
            event_type=event_type,
            status=status,
            message=message,
            metadata_json=metadata or {}
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def get_transaction_audit_trail(db: Session, transaction_id: str) -> List[AuditEvent]:
        return list(
            db.scalars(
                select(AuditEvent)
                .where(AuditEvent.transaction_id == transaction_id)
                .order_by(AuditEvent.timestamp.asc())
            ).all()
        )
