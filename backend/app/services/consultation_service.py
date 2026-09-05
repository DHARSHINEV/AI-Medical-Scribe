from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clinical_alert import ClinicalAlert
from app.models.clinical_note import ClinicalNote
from app.models.consultation import Consultation
from app.schemas.consultation import ConsultationCreate
from app.services import audit_service


def get_consultation(
    db: Session,
    consultation_id: int,
) -> Consultation | None:
    return db.get(Consultation, consultation_id)


def get_patient_consultations(
    db: Session,
    patient_id: int,
) -> list[Consultation]:
    statement = (
        select(Consultation)
        .where(Consultation.patient_id == patient_id)
        .order_by(Consultation.created_at.desc())
    )
    return list(db.scalars(statement).all())


def create_consultation(
    db: Session,
    patient_id: int,
    data: ConsultationCreate,
    user_id: Optional[int] = None,
) -> Consultation:
    assigned_doctor_id = user_id if user_id is not None else data.doctor_id
    consultation = Consultation(
        patient_id=patient_id,
        doctor_id=assigned_doctor_id,
        status="draft",
        stage="idle",
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    audit_service.log_event(
        db,
        action="CONSULTATION_CREATED",
        user_id=assigned_doctor_id,
        consultation_id=consultation.id,
        details={"patient_id": patient_id},
    )

    return consultation


def update_audio(
    db: Session,
    consultation: Consultation,
    audio_path: str,
    user_id: Optional[int] = None,
) -> Consultation:
    consultation.audio_path = audio_path
    consultation.status = "draft"
    consultation.stage = "uploaded"

    db.commit()
    db.refresh(consultation)

    audit_service.log_event(
        db,
        action="AUDIO_UPLOADED",
        user_id=user_id or consultation.doctor_id,
        consultation_id=consultation.id,
        details={"audio_path": audio_path},
    )

    return consultation


def update_stage(
    db: Session,
    consultation: Consultation,
    stage: str,
    status: Optional[str] = None,
) -> Consultation:
    consultation.stage = stage
    if status:
        consultation.status = status
    db.commit()
    db.refresh(consultation)
    return consultation


def approve_consultation(
    db: Session,
    consultation: Consultation,
    approved_by: Optional[int] = None,
) -> Consultation:
    """
    Approve consultation and associated clinical note.
    Requirements:
    - Clinician ID provided (cannot be None)
    - Consultation exists
    - Consultation is not already approved (idempotency check)
    - Consultation is in valid review state (status == "review" and stage == "review")
    - Clinical note exists
    - No unresolved review-required safety alerts (requires_review == True and resolved == False)
    - Sets approved_at and approved_by on both tables
    - Status and stage -> approved
    - Records CONSULTATION_APPROVED audit log
    """
    if not approved_by:
        raise ValueError("A valid clinician ID is required to approve the consultation.")

    if consultation.status == "approved" or consultation.stage == "approved":
        raise ValueError("Consultation has already been approved.")

    if consultation.status != "review" or consultation.stage != "review":
        raise ValueError(
            f"Cannot approve consultation that is not in review state (current status: '{consultation.status}', stage: '{consultation.stage}')."
        )

    note = db.scalar(
        select(ClinicalNote).where(ClinicalNote.consultation_id == consultation.id)
    )
    if not note:
        raise ValueError("Cannot approve consultation without a generated clinical note.")

    # Check whether unresolved alerts with requires_review = True remain
    unresolved_review_alerts = list(
        db.scalars(
            select(ClinicalAlert).where(
                ClinicalAlert.consultation_id == consultation.id,
                ClinicalAlert.requires_review == True,
                ClinicalAlert.resolved == False,
            )
        ).all()
    )
    if unresolved_review_alerts:
        raise ValueError(
            "Cannot approve consultation while unresolved clinical safety alerts require review."
        )

    now = datetime.now(timezone.utc)

    note.approved = True
    note.approved_by = approved_by
    note.approved_at = now

    consultation.status = "approved"
    consultation.stage = "approved"
    consultation.approved_by = approved_by
    consultation.approved_at = now

    db.commit()
    db.refresh(consultation)
    db.refresh(note)

    audit_service.log_event(
        db,
        action="CONSULTATION_APPROVED",
        user_id=approved_by,
        consultation_id=consultation.id,
        details={
            "note_id": note.id,
            "approved_at": now.isoformat(),
        },
    )

    return consultation