import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False)
    ai_draft: Mapped[str] = mapped_column(Text, nullable=False)
    final_text: Mapped[str | None] = mapped_column(Text)
    tone_used: Mapped[str | None] = mapped_column(String(20))
    model_used: Mapped[str | None] = mapped_column(String(50))
    was_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    review: Mapped["Review"] = relationship("Review", back_populates="responses")
