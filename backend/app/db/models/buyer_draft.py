from sqlalchemy import String, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class BuyerDraft(Base):
    __tablename__ = "buyer_drafts"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    owner: Mapped[str] = mapped_column(String(80), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(40))
    data: Mapped[dict] = mapped_column(JSON)
    events: Mapped[list] = mapped_column(JSON, default=list)
    transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
