from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.schemas.consultation import (
    ConsultationApprovalResponse,
    ConsultationCreate,
    ConsultationResponse,
)
from app.services import (
    ai_pipeline_service,
    audio_service,
    audit_service,
    consultation_service,
    patient_service,
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
    current_user: Optional[User] = Depends(get_current_user),
):
    patient = patient_service.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )

    assigned_doctor_id = current_user.id if current_user else data.doctor_id
    create_data = ConsultationCreate(doctor_id=assigned_doctor_id)
    return consultation_service.create_consultation(
        db,
        patient_id,
        create_data,
        user_id=assigned_doctor_id,
    )


# Root alias for frontend convenience: POST /consultations with patientId in body
@router.post(
    "/consultations",
    response_model=ConsultationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_consultation_direct(
    data: dict,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    patient_id = data.get("patient_id") or data.get("patientId")
    if not patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="patient_id is required.",
        )
    patient = patient_service.get_patient(db, int(patient_id))
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )

    assigned_doctor_id = current_user.id if current_user else data.get("doctor_id")
    create_data = ConsultationCreate(doctor_id=assigned_doctor_id)
    return consultation_service.create_consultation(
        db,
        int(patient_id),
        create_data,
        user_id=assigned_doctor_id,
    )


@router.get(
    "/consultations/{consultation_id}",
    response_model=ConsultationResponse,
)
def get_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
):
    consultation = consultation_service.get_consultation(db, consultation_id)
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
    patient = patient_service.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )
    return consultation_service.get_patient_consultations(db, patient_id)


@router.post(
    "/consultations/{consultation_id}/audio",
)
async def upload_consultation_audio(
    consultation_id: int,
    file: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )

    upload_file = audio or file
    if not upload_file or not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is required in 'audio' or 'file' form field.",
        )

    try:
        audio_path = await audio_service.save_audio(
            consultation_id,
            upload_file,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    updated = consultation_service.update_audio(
        db,
        consultation,
        audio_path,
        user_id=current_user.id if current_user else None,
    )

    return {
        "id": updated.id,
        "patient_id": updated.patient_id,
        "patientId": str(updated.patient_id),
        "status": updated.status,
        "stage": updated.stage,
        "audio_path": updated.audio_path,
        "jobId": str(uuid4()),
        "created_at": updated.created_at,
        "updated_at": updated.updated_at,
    }


@router.post(
    "/consultations/{consultation_id}/approve",
    response_model=ConsultationApprovalResponse,
)
def approve_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clinician authentication is required to approve a consultation.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )

    if consultation.status == "approved" or consultation.stage == "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consultation has already been approved.",
        )

    try:
        updated = consultation_service.approve_consultation(
            db,
            consultation,
            approved_by=current_user.id,
        )
        return ConsultationApprovalResponse(
            id=updated.id,
            status=updated.status,
            stage=updated.stage,
            approved=True,
            approved_at=updated.approved_at,
            approved_by=updated.approved_by,
            message="Consultation and clinical note successfully approved.",
        )
    except ValueError as exc:
        msg = str(exc)
        if "already been approved" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        ) from exc


@router.post(
    "/consultations/{consultation_id}/process",
)
def process_full_consultation_pipeline(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Run full end-to-end AI pipeline through orchestrator."""
    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )

    if not consultation.audio_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio uploaded for this consultation.",
        )

    try:
        result = ai_pipeline_service.run_full_pipeline(
            db=db,
            consultation=consultation,
            user_id=current_user.id if current_user else None,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI pipeline failed: {exc}",
        ) from exc


@router.get(
    "/consultations/{consultation_id}/audit",
    response_model=list[AuditLogResponse],
)
@router.get(
    "/consultations/{consultation_id}/audit-logs",
    response_model=list[AuditLogResponse],
)
def get_consultation_audit_logs(
    consultation_id: int,
    db: Session = Depends(get_db),
):
    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )
    return audit_service.get_consultation_audit_logs(db, consultation_id)