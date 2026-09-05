from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.consultation import Consultation
from app.schemas.consultation import ConsultationCreate
from sqlalchemy.orm import Session

from app.models.consultation import Consultation

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

def attach_audio(
    db: Session,
    consultation: Consultation,
    audio_path: str,
) -> Consultation:
    consultation.audio_path = audio_path
    consultation.status = "draft"
    consultation.stage = "uploading"

    db.commit()
    db.refresh(consultation)

    return consultation

def create_consultation(
    db: Session,
    patient_id: int,
    data: ConsultationCreate,
) -> Consultation:
    consultation = Consultation(
        patient_id=patient_id,
        doctor_id=data.doctor_id,
        status="draft",
        stage="idle",
    )

    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    return consultation

def update_audio(
    db: Session,
    consultation: Consultation,
    audio_path: str,
) -> Consultation:
    consultation.audio_path = audio_path
    consultation.status = "draft"
    consultation.stage = "uploading"

    db.commit()
    db.refresh(consultation)

    return consultation