from datetime import datetime, timezone
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.context.history_context import PatientHistoryContext
from app.ai.extraction.entity_extractor import ClinicalEntityExtractor
from app.ai.generation.soap_generator import SOAPGenerator
from app.models.clinical_note import ClinicalNote
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.models.transcript import TranscriptSegment
from app.schemas.soap import SOAPNoteUpdate
from app.services import audit_service, consultation_service

logger = logging.getLogger(__name__)


def generate_soap_note(
    db: Session,
    consultation: Consultation,
    user_id: Optional[int] = None,
) -> ClinicalNote:
    """
    Generate or regenerate a SOAP note for the given consultation.
    Grounds output in transcript, extracted entities, and actual database Patient context.
    Retry safety: Updates the existing draft note if already generated.
    """
    segments = list(
        db.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.consultation_id == consultation.id)
            .order_by(TranscriptSegment.start_time.asc())
        ).all()
    )
    if not segments:
        raise ValueError("Cannot generate SOAP note: transcript is missing.")

    # 1. Update stage
    consultation_service.update_stage(
        db,
        consultation,
        stage="generating",
        status="processing",
    )

    try:
        full_transcript = " ".join(s.text for s in segments)

        # 2. Extract entities in legacy dict format for SOAP synthesis
        extractor = ClinicalEntityExtractor()
        entity_dict = extractor.extract(full_transcript)

        # 3. Retrieve database Patient record as source of truth for history context
        patient = db.get(Patient, consultation.patient_id)
        history_dict = (
            PatientHistoryContext.from_patient_model(patient) if patient else {}
        )

        history_context = PatientHistoryContext().build_context(
            patient_history=history_dict,
            current_entities=entity_dict,
        )

        # 4. Generate structured SOAP note
        generator = SOAPGenerator(mode="demo")
        generated = generator.generate(
            transcript=full_transcript,
            entities=entity_dict,
            patient_history_context=history_context,
        )

        # 5. Retry safety: Update existing note or insert new one
        existing_note = db.scalar(
            select(ClinicalNote).where(
                ClinicalNote.consultation_id == consultation.id
            )
        )

        if existing_note:
            existing_note.subjective = generated["subjective"]
            existing_note.objective = generated["objective"]
            existing_note.assessment = generated["assessment"]
            existing_note.plan = generated["plan"]
            existing_note.approved = False
            existing_note.approved_by = None
            existing_note.approved_at = None
            note = existing_note
        else:
            note = ClinicalNote(
                consultation_id=consultation.id,
                subjective=generated["subjective"],
                objective=generated["objective"],
                assessment=generated["assessment"],
                plan=generated["plan"],
                approved=False,
                approved_by=None,
                approved_at=None,
            )
            db.add(note)

        db.commit()
        db.refresh(note)

        # 6. Update stage to generated
        consultation_service.update_stage(
            db,
            consultation,
            stage="generated",
            status="processing",
        )

        audit_service.log_event(
            db,
            action="SOAP_GENERATED",
            user_id=user_id or consultation.doctor_id,
            consultation_id=consultation.id,
            details={"note_id": note.id},
        )

        return note

    except Exception as exc:
        db.rollback()
        consultation_service.update_stage(
            db,
            consultation,
            stage="error",
            status="failed",
        )
        logger.error(f"SOAP note generation failed for consultation {consultation.id}: {exc}")
        raise


def get_soap_note(
    db: Session,
    consultation_id: int,
) -> Optional[ClinicalNote]:
    statement = select(ClinicalNote).where(
        ClinicalNote.consultation_id == consultation_id
    )
    return db.scalar(statement)


def update_soap_note(
    db: Session,
    note: ClinicalNote,
    update_data: SOAPNoteUpdate,
    user_id: Optional[int] = None,
) -> ClinicalNote:
    """Allow clinician to manually edit and refine the draft SOAP note."""
    data = update_data.model_dump(exclude_unset=True)
    for field, value in data.items():
        if value is not None:
            setattr(note, field, value)

    note.approved = False
    note.approved_by = None
    note.approved_at = None
    note.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(note)

    audit_service.log_event(
        db,
        action="CLINICAL_NOTE_UPDATED",
        user_id=user_id,
        consultation_id=note.consultation_id,
        details={"note_id": note.id, "fields_updated": list(data.keys())},
    )

    return note
