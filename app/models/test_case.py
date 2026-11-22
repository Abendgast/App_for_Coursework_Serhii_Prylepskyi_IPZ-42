from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import CheckConstraint, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.test_suite import TestSuite


class TestCase(Base):
    __tablename__ = "test_cases"
    __table_args__ = (
        CheckConstraint("status IN ('passed', 'failed', 'skipped')", name="status_is_valid"),
        CheckConstraint("duration_seconds >= 0", name="duration_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    suite_id: Mapped[str] = mapped_column(
        ForeignKey("test_suites.id", ondelete="CASCADE"), index=True, nullable=False
    )
    classname: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    suite: Mapped["TestSuite"] = relationship(back_populates="cases")
