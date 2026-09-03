from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class MerchantPolicy(Base):
    __tablename__ = "merchant_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False, default="default_policy")

    # Hard Commercial Constraints
    min_margin_percent: Mapped[float] = mapped_column(Float, nullable=False, default=15.0)
    max_discount_percent: Mapped[float] = mapped_column(Float, nullable=False, default=20.0)
    allow_bundles: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_substitutions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Scoring Weights for Deterministic Ranker
    weight_margin: Mapped[float] = mapped_column(Float, nullable=False, default=0.4)
    weight_revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    weight_overstock: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    weight_discount_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)

    # Metadata & Timestamps
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<MerchantPolicy(name='{self.policy_name}', min_margin={self.min_margin_percent}%, max_discount={self.max_discount_percent}%)>"
