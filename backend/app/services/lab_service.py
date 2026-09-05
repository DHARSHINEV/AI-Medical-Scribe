import logging
from pathlib import Path
from typing import List, Optional
import uuid
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.lab_report import LabReport
from app.models.patient import Patient
from app.services import audit_service

logger = logging.getLogger(__name__)

ALLOWED_LAB_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

MAX_LAB_FILE_SIZE = settings.max_audio_size_mb * 1024 * 1024


async def save_lab_report(
    db: Session,
    patient_id: int,
    file: UploadFile,
    title: Optional[str] = None,
    consultation_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> LabReport:
    """Save an uploaded lab report file to disk and record metadata in database."""
    patient = db.get(Patient, patient_id)
    if not patient:
        raise ValueError(f"Patient with ID {patient_id} not found.")

    original_name = file.filename or "lab_report.pdf"
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_LAB_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: '{extension}'. Allowed formats: PDF, PNG, JPG, JPEG."
        )

    mime_type = file.content_type or ALLOWED_LAB_EXTENSIONS[extension]

    upload_dir = Path(settings.upload_dir) / "lab_reports"
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"patient_{patient_id}_lab_{uuid.uuid4().hex}{extension}"
    destination = upload_dir / unique_filename

    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_LAB_FILE_SIZE:
                    destination.unlink(missing_ok=True)
                    raise ValueError("Lab report file exceeds maximum allowed size (50MB).")
                output.write(chunk)
    finally:
        await file.close()

    report_title = title.strip() if (title and title.strip()) else Path(original_name).stem.replace("_", " ").title()

    report = LabReport(
        patient_id=patient_id,
        consultation_id=consultation_id,
        title=report_title,
        filename=original_name,
        file_path=str(destination),
        file_size_bytes=size,
        mime_type=mime_type,
        uploaded_by=user_id,
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    audit_service.log_event(
        db,
        action="LAB_REPORT_UPLOADED",
        user_id=user_id,
        consultation_id=consultation_id,
        details={
            "lab_id": report.id,
            "patient_id": patient_id,
            "filename": original_name,
            "file_size_bytes": size,
            "mime_type": mime_type,
        },
    )

    return report


def get_patient_lab_reports(db: Session, patient_id: int) -> List[LabReport]:
    """Retrieve all lab reports associated with a specific patient."""
    statement = (
        select(LabReport)
        .where(LabReport.patient_id == patient_id)
        .order_by(LabReport.created_at.desc())
    )
    return list(db.scalars(statement).all())


def get_all_lab_reports(db: Session) -> List[LabReport]:
    """Retrieve all lab reports across the clinic."""
    statement = select(LabReport).order_by(LabReport.created_at.desc())
    return list(db.scalars(statement).all())


def get_lab_report(db: Session, lab_id: int) -> Optional[LabReport]:
    """Retrieve a single lab report by ID."""
    return db.get(LabReport, lab_id)


def delete_lab_report(db: Session, lab_id: int, user_id: Optional[int] = None) -> bool:
    """Delete a lab report record and its file from storage."""
    report = db.get(LabReport, lab_id)
    if not report:
        return False

    file_path = Path(report.file_path)
    file_path.unlink(missing_ok=True)

    db.delete(report)
    db.commit()

    audit_service.log_event(
        db,
        action="LAB_REPORT_DELETED",
        user_id=user_id,
        consultation_id=report.consultation_id,
        details={
            "lab_id": lab_id,
            "patient_id": report.patient_id,
            "filename": report.filename,
        },
    )
    return True
