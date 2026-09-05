import logging
from typing import List, Optional
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.diarization.diarizer import SpeakerDiarizer
from app.ai.transcription.transcriber import SpeechToText
from app.core.config import settings
from app.models.consultation import Consultation
from app.models.transcript import TranscriptSegment
from app.services import audit_service, consultation_service

logger = logging.getLogger(__name__)


def transcribe_consultation(
    db: Session,
    consultation: Consultation,
    user_id: Optional[int] = None,
) -> List[TranscriptSegment]:
    """
    Transcribe audio for a consultation and persist timestamped segments.
    Idempotent on retry: Removes existing segments for this consultation before persisting new ones.
    """
    if not consultation.audio_path:
        raise ValueError("No audio uploaded for this consultation.")

    # 1. Update stage
    consultation_service.update_stage(
        db,
        consultation,
        stage="transcribing",
        status="processing",
    )

    try:
        # 2. Call Faster-Whisper through singleton model manager
        transcriber = SpeechToText(model_size=settings.whisper_model)
        result = transcriber.transcribe(consultation.audio_path)

        raw_segments = result.get("segments", [])
        if not raw_segments and result.get("text", "").strip():
            raw_segments = [
                {
                    "start": 0.0,
                    "end": 0.0,
                    "text": result.get("text", "").strip(),
                }
            ]

        # 3. Apply speaker identification / alternation fallback
        diarizer = SpeakerDiarizer()
        diarized_segments = diarizer.diarize(raw_segments)

        # 4. Retry safety: delete existing segments for this consultation
        db.execute(
            delete(TranscriptSegment).where(
                TranscriptSegment.consultation_id == consultation.id
            )
        )
        db.flush()

        # 5. Save TranscriptSegment rows
        saved_segments: List[TranscriptSegment] = []
        for seg in diarized_segments:
            record = TranscriptSegment(
                consultation_id=consultation.id,
                speaker=seg.get("speaker", "Unassigned"),
                text=seg.get("text", "").strip(),
                start_time=float(seg.get("start", 0.0)),
                end_time=float(seg.get("end", 0.0)),
                confidence=seg.get("confidence"),
            )
            db.add(record)
            saved_segments.append(record)

        db.commit()
        for rec in saved_segments:
            db.refresh(rec)

        # 6. Update stage to transcribed
        consultation_service.update_stage(
            db,
            consultation,
            stage="transcribed",
            status="processing",
        )

        audit_service.log_event(
            db,
            action="TRANSCRIPTION_COMPLETED",
            user_id=user_id or consultation.doctor_id,
            consultation_id=consultation.id,
            details={
                "segment_count": len(saved_segments),
                "language": result.get("language", "en"),
            },
        )

        return saved_segments

    except Exception as exc:
        db.rollback()
        consultation_service.update_stage(
            db,
            consultation,
            stage="error",
            status="failed",
        )
        logger.error(f"Transcription failed for consultation {consultation.id}: {exc}")
        raise


def get_transcript_segments(
    db: Session,
    consultation_id: int,
) -> List[TranscriptSegment]:
    statement = (
        select(TranscriptSegment)
        .where(TranscriptSegment.consultation_id == consultation_id)
        .order_by(TranscriptSegment.start_time.asc())
    )
    return list(db.scalars(statement).all())
