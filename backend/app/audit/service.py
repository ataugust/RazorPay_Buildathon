from typing import List, Dict, Any
from datetime import datetime
from sqlmodel import Session, select
from app.db.database import engine
from app.domain.models import AuditEvent, EventStatus

class AuditService:
    @staticmethod
    def log_event(
        transaction_id: str,
        component: str,
        event_type: str,
        status: EventStatus,
        message: str,
        metadata: Dict[str, Any] = None
    ) -> AuditEvent:
        event = AuditEvent(
            timestamp=datetime.utcnow(),
            transaction_id=transaction_id,
            component=component,
            event_type=event_type,
            status=status,
            message=message,
            metadata_json=metadata or {}
        )
        with Session(engine) as session:
            session.add(event)
            session.commit()
            session.refresh(event)
        return event

    @staticmethod
    def get_events_for_transaction(transaction_id: str) -> List[AuditEvent]:
        with Session(engine) as session:
            statement = select(AuditEvent).where(AuditEvent.transaction_id == transaction_id).order_by(AuditEvent.timestamp)
            return list(session.exec(statement).all())
