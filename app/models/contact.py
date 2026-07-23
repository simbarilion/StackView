"""ORM-модель сохранённого обращения с формы обратной связи"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ContactSubmission(Base):
    """Обращение пользователя"""

    __tablename__ = "contact_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)

    email_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    suggested_reply: Mapped[str | None] = mapped_column(Text, nullable=True)

    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IP клиента для антиспама/аудита
