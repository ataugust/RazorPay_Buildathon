from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    component: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "CONTROL_PLANE", "MARGIN_GATE", "SPECIFICATION_GATE"
    event_type: Mapped[str] = mapped_column(String(100), nullable=False) # e.g., "GATE_CHECK", "OFFER_APPROVED", "OFFER_REJECTED"
    status: Mapped[str] = mapped_column(String(20), nullable=False)      # "PASS", "FAIL", "INFO", "WARN"
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditEvent(txn='{self.transaction_id}', component='{self.component}', status='{self.status}')>"
