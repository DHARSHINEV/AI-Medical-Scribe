from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.transcript import FullTranscriptResponse, TranscriptSegmentResponse
from app.services import (
    clinical_service,
    consultation_service,
    note_service,
    safety_service,
    transcription_service,
)

router = APIRouter(
    prefix="/api/consultations",
    tags=["Transcription"],
)


@router.post(
    "/{consultation_id}/transcribe",
    response_model=List[TranscriptSegmentResponse],
)
def transcribe_consultation(
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

    if not consultation.audio_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio has been uploaded for this consultation.",
        )

    try:
        user_id = current_user.id if current_user else None
        segments = transcription_service.transcribe_consultation(
            db=db,
            consultation=consultation,
            user_id=user_id,
        )

        # Downstream AI pipeline persistence
        clinical_service.extract_clinical_entities(
            db=db,
            consultation=consultation,
            user_id=user_id,
        )
        note_service.generate_soap_note(
            db=db,
            consultation=consultation,
            user_id=user_id,
        )
        safety_service.validate_consultation_safety(
            db=db,
            consultation=consultation,
            user_id=user_id,
        )

        return segments
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {exc}",
        ) from exc


@router.get(
    "/{consultation_id}/transcript",
    response_model=List[TranscriptSegmentResponse],
)
def get_consultation_transcript(
    consultation_id: int,
    db: Session = Depends(get_db),
):
    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )

    segments = transcription_service.get_transcript_segments(db, consultation_id)
    return segments
