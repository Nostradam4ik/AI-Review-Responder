from sqlalchemy import String, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    stripe_price_id: Mapped[str] = mapped_column(String(100), default="")
    price_eur: Mapped[int] = mapped_column(Integer, nullable=False)
    max_locations: Mapped[int] = mapped_column(Integer, nullable=False)
    max_responses_per_month: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 = unlimited
    features: Mapped[dict] = mapped_column(JSONB, default=dict)

    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="plan"
    )
