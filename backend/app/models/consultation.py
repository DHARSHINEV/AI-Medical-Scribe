from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Consultation(Base):
    __tablename__ = "consultations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )

    doctor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="draft",
    )

    stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="idle",
    )

    audio_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    patient = relationship("Patient")
    doctor = relationship("User", foreign_keys=[doctor_id])
    approver = relationship("User", foreign_keys=[approved_by])

    segments = relationship(
        "TranscriptSegment",
        back_populates="consultation",
        cascade="all, delete-orphan",
        order_by="TranscriptSegment.start_time",
    )
    clinical_entities = relationship(
        "ClinicalEntity",
        back_populates="consultation",
        cascade="all, delete-orphan",
    )
    clinical_note = relationship(
        "ClinicalNote",
        back_populates="consultation",
        uselist=False,
        cascade="all, delete-orphan",
    )
    alerts = relationship(
        "ClinicalAlert",
        back_populates="consultation",
        cascade="all, delete-orphan",
    )