from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.test_case import TestCase
    from app.models.test_run import TestRun


class TestSuite(Base):
    __tablename__ = "test_suites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        ForeignKey("test_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    run: Mapped["TestRun"] = relationship(back_populates="suites")
    cases: Mapped[list["TestCase"]] = relationship(
        back_populates="suite", cascade="all, delete-orphan", passive_deletes=True
    )
