from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Deal(Base):
    __tablename__ = "deals"

    transaction_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    product_query: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    max_budget_paise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    outcome_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    recovered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    merchant_response_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    intelligence_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    initial_offer_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    current_offer_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    candidates_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    gate_results_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
