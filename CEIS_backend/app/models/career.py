import uuid
import random
from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_application_id() -> str:
    return f"CE-APP-{random.randint(1000, 9999)}"


class CareerRole(Base):
    __tablename__ = "career_roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    department: Mapped[str] = mapped_column(String(80), nullable=False)
    location: Mapped[str] = mapped_column(
        String(120), default="Indore, MP (On-Site / Hybrid)", nullable=False
    )
    employment_type: Mapped[str] = mapped_column(String(50), default="Full-Time", nullable=False)
    experience: Mapped[str | None] = mapped_column(String(60), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    applications: Mapped[list["JobApplication"]] = relationship(
        "JobApplication", back_populates="role"
    )


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, default=generate_application_id
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("career_roles.id", ondelete="SET NULL"), nullable=True
    )
    role_title: Mapped[str] = mapped_column(String(140), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    portfolio_url: Mapped[str] = mapped_column(Text, nullable=False)
    resume_url: Mapped[str] = mapped_column(Text, nullable=False)
    cover_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="received", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_job_applications_email_role", "email", "role_title"),
    )

    role: Mapped["CareerRole | None"] = relationship("CareerRole", back_populates="applications")
