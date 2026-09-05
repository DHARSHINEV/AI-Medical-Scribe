import logging
from typing import List, Optional
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.extraction.entity_extractor import ClinicalEntityExtractor
from app.models.clinical_entity import ClinicalEntity
from app.models.consultation import Consultation
from app.models.transcript import TranscriptSegment
from app.services import audit_service, consultation_service

logger = logging.getLogger(__name__)


def extract_clinical_entities(
    db: Session,
    consultation: Consultation,
    user_id: Optional[int] = None,
) -> List[ClinicalEntity]:
    """
    Extract clinical entities from the consultation transcript segments.
    Preserves negation, status, and links evidence segments.
    Retry safety: Deletes previously extracted entities for this consultation.
    """
    segments = list(
        db.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.consultation_id == consultation.id)
            .order_by(TranscriptSegment.start_time.asc())
        ).all()
    )

    if not segments:
        raise ValueError("Cannot extract clinical entities: consultation transcript is empty.")

    # 1. Update stage
    consultation_service.update_stage(
        db,
        consultation,
        stage="extracting",
        status="processing",
    )

    try:
        extractor = ClinicalEntityExtractor()

        # Format segments for segment-level evidence linkage
        segment_dicts = [
            {
                "id": s.id,
                "text": s.text,
                "speaker": s.speaker,
                "start": s.start_time,
                "end": s.end_time,
            }
            for s in segments
        ]
        full_transcript = " ".join(s.text for s in segments)

        structured_results = extractor.extract_structured(
            text=full_transcript,
            segments=segment_dicts,
        )

        # 2. Retry safety: delete previous entities for this consultation
        db.execute(
            delete(ClinicalEntity).where(
                ClinicalEntity.consultation_id == consultation.id
            )
        )
        db.flush()

        # 3. Save new ClinicalEntity rows
        saved_entities: List[ClinicalEntity] = []
        for item in structured_results:
            entity = ClinicalEntity(
                consultation_id=consultation.id,
                type=item["type"],
                value=item["value"],
                label=item.get("label"),
                status=item.get("status", "present"),
                confidence=item.get("confidence"),
                evidence_segment_id=item.get("evidence_segment_id"),
            )
            db.add(entity)
            saved_entities.append(entity)

        db.commit()
        for ent in saved_entities:
            db.refresh(ent)

        # 4. Update stage to extracted
        consultation_service.update_stage(
            db,
            consultation,
            stage="extracted",
            status="processing",
        )

        audit_service.log_event(
            db,
            action="CLINICAL_EXTRACTION_COMPLETED",
            user_id=user_id or consultation.doctor_id,
            consultation_id=consultation.id,
            details={"entity_count": len(saved_entities)},
        )

        return saved_entities

    except Exception as exc:
        db.rollback()
        consultation_service.update_stage(
            db,
            consultation,
            stage="error",
            status="failed",
        )
        logger.error(f"Clinical extraction failed for consultation {consultation.id}: {exc}")
        raise


def get_clinical_entities(
    db: Session,
    consultation_id: int,
) -> List[ClinicalEntity]:
    statement = (
        select(ClinicalEntity)
        .where(ClinicalEntity.consultation_id == consultation_id)
        .order_by(ClinicalEntity.id.asc())
    )
    return list(db.scalars(statement).all())
