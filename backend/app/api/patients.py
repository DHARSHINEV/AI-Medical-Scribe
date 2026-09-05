from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.consultation import ConsultationResponse
from app.schemas.patient import (
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)
from app.services import consultation_service, patient_service

router = APIRouter(
    prefix="/api/patients",
    tags=["Patients"],
)


@router.get(
    "",
    response_model=list[PatientResponse],
)
def list_patients(
    db: Session = Depends(get_db),
):
    return patient_service.get_patients(db)


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient(
    patient: PatientCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    existing = patient_service.get_patient_by_mrn(
        db,
        patient.mrn,
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Patient with this MRN already exists.",
        )

    return patient_service.create_patient(
        db,
        patient,
        user_id=current_user.id if current_user else None,
    )


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
):
    patient = patient_service.get_patient(
        db,
        patient_id,
    )

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )

    return patient


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
)
def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db),
):
    patient = patient_service.get_patient(
        db,
        patient_id,
    )

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )

    return patient_service.update_patient(
        db,
        patient,
        patient_data,
    )


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
):
    patient = patient_service.get_patient(
        db,
        patient_id,
    )

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )

    patient_service.delete_patient(
        db,
        patient,
    )


@router.get(
    "/{patient_id}/history",
    response_model=list[ConsultationResponse],
)
def get_patient_history(
    patient_id: int,
    db: Session = Depends(get_db),
):
    patient = patient_service.get_patient(
        db,
        patient_id,
    )
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )

    return patient_service.get_patient_history(db, patient_id)