from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.lab_report import LabReportResponse
from app.services import consultation_service, lab_service, patient_service

router = APIRouter(
    tags=["Laboratory Reports"],
)


def _serialize_lab_report(report) -> LabReportResponse:
    return LabReportResponse(
        id=report.id,
        patient_id=report.patient_id,
        consultation_id=report.consultation_id,
        title=report.title,
        filename=report.filename,
        file_size_bytes=report.file_size_bytes,
        mime_type=report.mime_type,
        uploaded_by=report.uploaded_by,
        created_at=report.created_at,
        file_url=f"/api/labs/{report.id}/file",
    )


@router.post(
    "/api/patients/{patient_id}/labs",
    response_model=LabReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_patient_lab_report(
    patient_id: int,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    consultation_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Upload a real diagnostic laboratory report (PDF/Image) for a patient."""
    patient = patient_service.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )

    try:
        report = await lab_service.save_lab_report(
            db=db,
            patient_id=patient_id,
            file=file,
            title=title,
            consultation_id=consultation_id,
            user_id=current_user.id if current_user else None,
        )
        return _serialize_lab_report(report)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/api/consultations/{consultation_id}/labs",
    response_model=LabReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_consultation_lab_report(
    consultation_id: int,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Upload a lab report associated directly with an active consultation encounter."""
    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )

    try:
        report = await lab_service.save_lab_report(
            db=db,
            patient_id=consultation.patient_id,
            file=file,
            title=title,
            consultation_id=consultation_id,
            user_id=current_user.id if current_user else None,
        )
        return _serialize_lab_report(report)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/api/patients/{patient_id}/labs",
    response_model=List[LabReportResponse],
)
def get_patient_lab_reports(
    patient_id: int,
    db: Session = Depends(get_db),
):
    """Get all laboratory reports for a patient."""
    patient = patient_service.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )

    reports = lab_service.get_patient_lab_reports(db, patient_id)
    return [_serialize_lab_report(r) for r in reports]


@router.get(
    "/api/labs",
    response_model=List[LabReportResponse],
)
def list_all_lab_reports(
    db: Session = Depends(get_db),
):
    """List all laboratory reports across all clinic patients."""
    reports = lab_service.get_all_lab_reports(db)
    return [_serialize_lab_report(r) for r in reports]


@router.get(
    "/api/labs/{lab_id}",
    response_model=LabReportResponse,
)
def get_lab_report(
    lab_id: int,
    db: Session = Depends(get_db),
):
    """Get metadata for a specific lab report."""
    report = lab_service.get_lab_report(db, lab_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab report not found.",
        )
    return _serialize_lab_report(report)


@router.get(
    "/api/labs/{lab_id}/file",
)
@router.get(
    "/api/labs/{lab_id}/download",
)
def download_lab_report_file(
    lab_id: int,
    db: Session = Depends(get_db),
):
    """Serve the raw PDF or image lab report file for browser viewing / downloading."""
    report = lab_service.get_lab_report(db, lab_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab report not found.",
        )

    file_path = Path(report.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab report file is missing on storage.",
        )

    return FileResponse(
        path=str(file_path),
        media_type=report.mime_type,
        filename=report.filename,
    )


@router.delete(
    "/api/labs/{lab_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_lab_report(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Delete a laboratory report."""
    success = lab_service.delete_lab_report(
        db=db,
        lab_id=lab_id,
        user_id=current_user.id if current_user else None,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab report not found.",
        )
