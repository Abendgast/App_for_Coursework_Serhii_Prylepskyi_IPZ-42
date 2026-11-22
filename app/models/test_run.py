from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.test_attachment import TestAttachment
    from app.models.test_suite import TestSuite


class TestRun(Base):
    __tablename__ = "test_runs"
    __table_args__ = (
        CheckConstraint("total_tests >= 0", name="total_tests_nonnegative"),
        CheckConstraint("passed_tests >= 0", name="passed_tests_nonnegative"),
        CheckConstraint("failed_tests >= 0", name="failed_tests_nonnegative"),
        CheckConstraint("skipped_tests >= 0", name="skipped_tests_nonnegative"),
        CheckConstraint("duration_seconds >= 0", name="duration_nonnegative"),
        CheckConstraint("pass_rate >= 0 AND pass_rate <= 100", name="pass_rate_range"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    report_format: Mapped[str] = mapped_column(String(10), nullable=False)
    build_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    total_tests: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_tests: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_tests: Mapped[int] = mapped_column(Integer, nullable=False)
    skipped_tests: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    pass_rate: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    project: Mapped["Project"] = relationship(back_populates="runs")
    suites: Mapped[list["TestSuite"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )
    attachment: Mapped["TestAttachment"] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )
