from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.soap import SOAPNoteResponse, SOAPNoteUpdate
from app.services import consultation_service, note_service

router = APIRouter(
    prefix="/api/consultations",
    tags=["Clinical Notes / SOAP"],
)


@router.post(
    "/{consultation_id}/generate-note",
    response_model=SOAPNoteResponse,
)
@router.post(
    "/{consultation_id}/soap",
    response_model=SOAPNoteResponse,
)
def generate_soap_note(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )

    try:
        note = note_service.generate_soap_note(
            db=db,
            consultation=consultation,
            user_id=current_user.id if current_user else None,
        )
        return note
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SOAP note generation failed: {exc}",
        ) from exc


@router.get(
    "/{consultation_id}/note",
    response_model=SOAPNoteResponse,
)
@router.get(
    "/{consultation_id}/soap",
    response_model=SOAPNoteResponse,
)
def get_soap_note(
    consultation_id: int,
    db: Session = Depends(get_db),
):
    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )

    note = note_service.get_soap_note(db, consultation_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical note has not been generated for this consultation.",
        )

    return note


@router.put(
    "/{consultation_id}/note",
    response_model=SOAPNoteResponse,
)
@router.put(
    "/{consultation_id}/soap",
    response_model=SOAPNoteResponse,
)
def update_soap_note(
    consultation_id: int,
    update_data: SOAPNoteUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )

    # Authorization check
    if current_user and consultation.doctor_id:
        if current_user.id != consultation.doctor_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to edit this consultation's clinical note.",
            )

    note = note_service.get_soap_note(db, consultation_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical note has not been generated yet.",
        )

    if note.consultation_id != consultation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note does not belong to the specified consultation.",
        )

    if note.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approved notes cannot be modified without formal revision.",
        )

    return note_service.update_soap_note(
        db=db,
        note=note,
        update_data=update_data,
        user_id=current_user.id if current_user else consultation.doctor_id,
    )
