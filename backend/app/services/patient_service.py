from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.consultation import Consultation
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services import audit_service


def get_patient(
    db: Session,
    patient_id: int,
) -> Patient | None:
    return db.get(Patient, patient_id)


def get_patient_by_mrn(
    db: Session,
    mrn: str,
) -> Patient | None:
    statement = select(Patient).where(Patient.mrn == mrn)
    return db.scalar(statement)


def get_patients(
    db: Session,
) -> list[Patient]:
    statement = select(Patient).order_by(Patient.created_at.desc())
    return list(db.scalars(statement).all())


def create_patient(
    db: Session,
    data: PatientCreate,
    user_id: Optional[int] = None,
) -> Patient:
    patient = Patient(
        mrn=data.mrn,
        name=data.name,
        age=data.age,
        gender=data.gender,
        conditions=data.conditions,
        allergies=data.allergies,
        medications=data.medications,
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    audit_service.log_event(
        db,
        action="PATIENT_CREATED",
        user_id=user_id,
        details={"patient_id": patient.id, "mrn": patient.mrn},
    )

    return patient


def update_patient(
    db: Session,
    patient: Patient,
    data: PatientUpdate,
) -> Patient:
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)

    return patient


def delete_patient(
    db: Session,
    patient: Patient,
) -> None:
    db.delete(patient)
    db.commit()


def get_patient_history(
    db: Session,
    patient_id: int,
) -> list[Consultation]:
    statement = (
        select(Consultation)
        .where(Consultation.patient_id == patient_id)
        .order_by(Consultation.created_at.desc())
    )
    return list(db.scalars(statement).all())