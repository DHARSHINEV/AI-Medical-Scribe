from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationResponse,
)
from app.services import consultation_service
from app.services import patient_service
from app.services import audio_service
from app.services import consultation_service
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)


router = APIRouter(
    prefix="/api",
    tags=["Consultations"],
)


@router.post(
    "/patients/{patient_id}/consultations",
    response_model=ConsultationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_consultation(
    patient_id: int,
    data: ConsultationCreate,
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

    return consultation_service.create_consultation(
        db,
        patient_id,
        data,
    )


@router.get(
    "/consultations/{consultation_id}",
    response_model=ConsultationResponse,
)
def get_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
):
    consultation = consultation_service.get_consultation(
        db,
        consultation_id,
    )

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )

    return consultation


@router.get(
    "/patients/{patient_id}/consultations",
    response_model=list[ConsultationResponse],
)
def list_patient_consultations(
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

    return consultation_service.get_patient_consultations(
        db,
        patient_id,
    )

@router.post(
    "/consultations/{consultation_id}/audio",
    response_model=ConsultationResponse,
)
async def upload_consultation_audio(
    consultation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    consultation = consultation_service.get_consultation(
        db,
        consultation_id,
    )

    if not consultation:
        raise HTTPException(
            status_code=404,
            detail="Consultation not found.",
        )

    try:
        audio_path = await audio_service.save_audio(
            consultation_id,
            file,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return consultation_service.update_audio(
        db,
        consultation,
        audio_path,
    )