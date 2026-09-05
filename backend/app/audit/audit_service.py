from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import func, select
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

    @staticmethod
    def get_transaction_events_after(
        db: Session,
        transaction_id: str,
        after_id: int = 0,
    ) -> List[AuditEvent]:
        return list(
            db.scalars(
                select(AuditEvent)
                .where(AuditEvent.transaction_id == transaction_id)
                .where(AuditEvent.id > after_id)
                .order_by(AuditEvent.id.asc())
            ).all()
        )

    @staticmethod
    def get_recent_events(db: Session, limit: int = 50) -> List[AuditEvent]:
        return list(
            db.scalars(
                select(AuditEvent)
                .order_by(AuditEvent.timestamp.desc())
                .limit(limit)
            ).all()
        )

    @staticmethod
    def get_operational_summary(db: Session) -> Dict[str, int]:
        total_transactions = db.scalar(
            select(func.count(func.distinct(AuditEvent.transaction_id)))
        ) or 0
        approved = db.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.event_type == "CANDIDATE_APPROVED"
            )
        ) or 0
        rejected = db.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.event_type == "CANDIDATE_REJECTED"
            )
        ) or 0
        passed_gates = db.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.event_type == "GATE_CHECK_PASS"
            )
        ) or 0
        failed_gates = db.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.event_type == "GATE_CHECK_FAIL"
            )
        ) or 0
        return {
            "total_transactions": total_transactions,
            "approved_transactions": approved,
            "rejected_transactions": rejected,
            "passed_gates": passed_gates,
            "failed_gates": failed_gates,
        }
