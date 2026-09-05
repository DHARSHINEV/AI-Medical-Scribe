from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ClinicalEntity(Base):
    __tablename__ = "clinical_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    consultation_id: Mapped[int] = mapped_column(
        ForeignKey("consultations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="present",
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_segment_id: Mapped[int | None] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    consultation = relationship("Consultation", back_populates="clinical_entities")
    evidence_segment = relationship("TranscriptSegment")
