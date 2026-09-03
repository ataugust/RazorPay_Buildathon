from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # Pricing & Inventory (Integer rupees, no floats for money)
    selling_price_rupees: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_price_rupees: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Laptop Specifications (Nullable for accessories/monitors)
    cpu_brand: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cpu_tier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cpu_generation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ram_gb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_gb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_inches: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    operating_system: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Merchant Metadata
    is_overstock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
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
        return f"<Product(sku='{self.sku}', name='{self.name}', category='{self.category}', sell={self.selling_price_rupees})>"
