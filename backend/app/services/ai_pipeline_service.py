import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.models.consultation import Consultation
from app.services import (
    clinical_service,
    consultation_service,
    note_service,
    safety_service,
    transcription_service,
)

logger = logging.getLogger(__name__)


def run_full_pipeline(
    db: Session,
    consultation: Consultation,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Orchestrate the end-to-end MediScribe AI pipeline across individual services:
    1. Audio Transcription & Diarization
    2. Clinical Entity Extraction (with negation)
    3. Patient Context Integration & SOAP Note Generation
    4. Clinical Second Look Safety Verification

    Each step is independently callable and manages its own database state and retry safety.
    """
    logger.info(f"Starting end-to-end AI pipeline for consultation {consultation.id}")

    try:
        # Step 1: Speech-to-Text and Speaker Diarization
        segments = transcription_service.transcribe_consultation(
            db=db,
            consultation=consultation,
            user_id=user_id,
        )

        # Step 2: Clinical Entity Extraction
        entities = clinical_service.extract_clinical_entities(
            db=db,
            consultation=consultation,
            user_id=user_id,
        )

        # Step 3: Patient Context & SOAP Generation
        note = note_service.generate_soap_note(
            db=db,
            consultation=consultation,
            user_id=user_id,
        )

        # Step 4: Clinical Second Look Safety Validation
        safety_output = safety_service.validate_consultation_safety(
            db=db,
            consultation=consultation,
            user_id=user_id,
        )

        logger.info(
            f"AI pipeline completed successfully for consultation {consultation.id}. Stage: review"
        )

        return {
            "consultation_id": consultation.id,
            "status": consultation.status,
            "stage": consultation.stage,
            "segment_count": len(segments),
            "entity_count": len(entities),
            "note_id": note.id,
            "alerts": safety_output.get("alerts", []),
            "review_required": safety_output.get("review_required", True),
        }

    except Exception as exc:
        logger.error(
            f"AI pipeline encountered an error for consultation {consultation.id}: {exc}"
        )
        consultation_service.update_stage(
            db,
            consultation,
            stage="error",
            status="failed",
        )
        raise
