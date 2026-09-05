import asyncio
import io
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uuid
import wave

import numpy as np
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.ai.diarization.diarizer import SpeakerDiarizer
from app.ai.transcription.transcriber import SpeechToText
from app.core.config import settings
from app.models.consultation import Consultation
from app.models.transcript import TranscriptSegment
from app.services import audit_service

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000  # 16 kHz Mono PCM16 standard
BYTES_PER_SAMPLE = 2  # 16-bit PCM = 2 bytes per sample
CHUNK_WINDOW_SECONDS = 2.0  # Transcribe window
MIN_SAMPLES_FOR_CHUNK = int(SAMPLE_RATE * CHUNK_WINDOW_SECONDS)


class AmbientSession:
    """
    Manages an active real-time ambient transcription session.
    Accumulates raw PCM16 audio, runs streaming Faster-Whisper, merges deduplicated
    segments, and finalizes authoritative consultation records.
    """

    def __init__(self, consultation_id: int, doctor_id: Optional[int] = None):
        self.consultation_id = consultation_id
        self.doctor_id = doctor_id
        self.session_id = str(uuid.uuid4())
        self.created_at = time.time()

        self.audio_bytes = bytearray()
        self.committed_sample_count = 0
        self.final_segments: List[Dict[str, Any]] = []
        self.sequence = 0
        self.speaker_diarizer = SpeakerDiarizer()
        self.transcriber = SpeechToText(model_size=settings.whisper_model, beam_size=1)
        self.is_paused = False
        self.is_finalized = False
        self.lock = asyncio.Lock()

        # Session-level two-speaker deterministic turn tracking
        # Speaker 1 (Initial conversation role) -> Doctor
        # Speaker 2 (Subsequent conversation role) -> Patient
        self.current_speaker: str = "Doctor"
        self.turn_index: int = 0
        self.last_speech_end_time: float = 0.0
        self.pause_threshold: float = 1.2  # Seconds of silence indicating a speaker turn transition

        # Timing instrumentation
        self.timing: Dict[str, Optional[float]] = {
            "capture_start": time.time(),
            "first_chunk_received": None,
            "first_partial_sent": None,
            "first_final_sent": None,
            "finalization_start": None,
            "final_transcript_completed": None,
        }

    def append_pcm16_chunk(self, chunk: bytes) -> None:
        """Append raw 16kHz 16-bit mono PCM bytes."""
        if self.is_paused or self.is_finalized:
            return
        if not self.timing["first_chunk_received"]:
            self.timing["first_chunk_received"] = time.time()
        self.audio_bytes.extend(chunk)

    async def process_incremental(self) -> List[Dict[str, Any]]:
        """
        Incrementally process active audio buffer.
        Returns a list of event dictionaries (transcript_partial or transcript_final)
        with deterministic Doctor/Patient speaker role assignment.
        """
        async with self.lock:
            if self.is_finalized:
                return []

            total_samples = len(self.audio_bytes) // BYTES_PER_SAMPLE
            new_samples = total_samples - self.committed_sample_count

            # Require minimum buffer before running Whisper inference
            if new_samples < MIN_SAMPLES_FOR_CHUNK:
                return []

            # Extract window from committed point to current end
            start_byte = self.committed_sample_count * BYTES_PER_SAMPLE
            window_bytes = bytes(self.audio_bytes[start_byte:])
            if not window_bytes:
                return []

            # Convert PCM16 to float32 NumPy array [-1.0, 1.0]
            audio_array = (
                np.frombuffer(window_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            )

            # Run Faster-Whisper in threadpool to keep event loop responsive
            loop = asyncio.get_running_loop()
            start_time_offset = self.committed_sample_count / float(SAMPLE_RATE)

            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: self.transcriber.transcribe(
                        audio_array,
                        beam_size=1,
                        vad_filter=True,
                    ),
                )
            except Exception as exc:
                logger.error(f"Ambient transcription step failed: {exc}")
                return []

            events: List[Dict[str, Any]] = []
            segments = result.get("segments", [])

            if not segments:
                # No speech detected in current window
                return []

            for seg in segments:
                seg_text = seg.get("text", "").strip()
                if not seg_text:
                    continue

                abs_start = round(start_time_offset + seg.get("start", 0.0), 2)
                abs_end = round(start_time_offset + seg.get("end", 0.0), 2)

                # Deterministic two-speaker role assignment:
                # If conversational pause between previous speech and this segment >= threshold,
                # transition speaker turn. Otherwise, maintain current speaker role.
                if self.last_speech_end_time > 0 and (abs_start - self.last_speech_end_time) >= self.pause_threshold:
                    self.turn_index += 1
                    self.current_speaker = "Doctor" if (self.turn_index % 2 == 0) else "Patient"

                speaker = self.current_speaker
                self.sequence += 1
                segment_id = f"ambient-{self.consultation_id}-{self.sequence}"

                # If segment ends well before current window edge (>0.5s silence), finalize it
                is_stable = (abs_end - start_time_offset) <= (len(audio_array) / SAMPLE_RATE - 0.5)

                if is_stable:
                    final_seg = {
                        "id": segment_id,
                        "sequence": self.sequence,
                        "speaker": speaker,
                        "text": seg_text,
                        "start_time": abs_start,
                        "end_time": abs_end,
                        "start_ms": int(abs_start * 1000),
                        "end_ms": int(abs_end * 1000),
                        "is_final": True,
                    }
                    self.final_segments.append(final_seg)
                    self.committed_sample_count = int(abs_end * SAMPLE_RATE)
                    self.last_speech_end_time = max(self.last_speech_end_time, abs_end)

                    if not self.timing["first_final_sent"]:
                        self.timing["first_final_sent"] = time.time()

                    events.append(
                        {
                            "type": "transcript_final",
                            "segment_id": segment_id,
                            "sequence": self.sequence,
                            "speaker": speaker,
                            "text": seg_text,
                            "start_ms": int(abs_start * 1000),
                            "end_ms": int(abs_end * 1000),
                        }
                    )
                else:
                    if not self.timing["first_partial_sent"]:
                        self.timing["first_partial_sent"] = time.time()

                    events.append(
                        {
                            "type": "transcript_partial",
                            "segment_id": segment_id,
                            "sequence": self.sequence,
                            "speaker": speaker,
                            "text": seg_text,
                            "start_ms": int(abs_start * 1000),
                            "end_ms": int(abs_end * 1000),
                        }
                    )

            return events

    async def finalize_session(
        self,
        db: Session,
        consultation: Consultation,
    ) -> Dict[str, Any]:
        """
        Stop capture, transcribe uncommitted tail audio, deduplicate segments,
        save full session audio to WAV, and persist segments to database.
        """
        async with self.lock:
            self.timing["finalization_start"] = time.time()
            self.is_finalized = True

            loop = asyncio.get_running_loop()

            # 1. Process any remaining uncommitted tail audio
            total_samples = len(self.audio_bytes) // BYTES_PER_SAMPLE
            if total_samples > self.committed_sample_count:
                start_byte = self.committed_sample_count * BYTES_PER_SAMPLE
                tail_bytes = bytes(self.audio_bytes[start_byte:])
                if len(tail_bytes) >= BYTES_PER_SAMPLE * 1600:  # >= 100ms
                    tail_array = (
                        np.frombuffer(tail_bytes, dtype=np.int16).astype(np.float32)
                        / 32768.0
                    )
                    start_time_offset = self.committed_sample_count / float(SAMPLE_RATE)
                    try:
                        result = await loop.run_in_executor(
                            None,
                            lambda: self.transcriber.transcribe(
                                tail_array,
                                beam_size=1,
                                vad_filter=False,
                            ),
                        )
                        for seg in result.get("segments", []):
                            seg_text = seg.get("text", "").strip()
                            if seg_text:
                                abs_start = round(start_time_offset + seg.get("start", 0.0), 2)
                                abs_end = round(start_time_offset + seg.get("end", 0.0), 2)
                                if self.last_speech_end_time > 0 and (abs_start - self.last_speech_end_time) >= self.pause_threshold:
                                    self.turn_index += 1
                                    self.current_speaker = "Doctor" if (self.turn_index % 2 == 0) else "Patient"

                                speaker = self.current_speaker
                                self.sequence += 1
                                self.final_segments.append(
                                    {
                                        "id": f"ambient-{self.consultation_id}-{self.sequence}",
                                        "sequence": self.sequence,
                                        "speaker": speaker,
                                        "text": seg_text,
                                        "start_time": abs_start,
                                        "end_time": abs_end,
                                        "start_ms": int(abs_start * 1000),
                                        "end_ms": int(abs_end * 1000),
                                        "is_final": True,
                                    }
                                )
                                self.last_speech_end_time = max(self.last_speech_end_time, abs_end)
                    except Exception as exc:
                        logger.warning(f"Tail audio final transcription error: {exc}")


            # 2. Deduplicate final segments chronologically
            deduped_segments: List[Dict[str, Any]] = []
            seen_texts = set()
            for s in sorted(self.final_segments, key=lambda x: x["start_time"]):
                normalized = s["text"].strip().lower()
                if normalized and normalized not in seen_texts:
                    seen_texts.add(normalized)
                    deduped_segments.append(s)

            # 3. Save full session WAV audio file to disk
            upload_dir = Path(settings.upload_dir)
            upload_dir.mkdir(parents=True, exist_ok=True)
            wav_filename = f"consultation_{self.consultation_id}_ambient_{uuid.uuid4().hex}.wav"
            wav_path = upload_dir / wav_filename

            def write_wav_file():
                with wave.open(str(wav_path), "wb") as wf:
                    wf.setnchannels(1)  # Mono
                    wf.setsampwidth(BYTES_PER_SAMPLE)  # 16-bit
                    wf.setframerate(SAMPLE_RATE)  # 16kHz
                    wf.writeframes(bytes(self.audio_bytes))

            if len(self.audio_bytes) > 0:
                await loop.run_in_executor(None, write_wav_file)
                consultation.audio_path = str(wav_path)

            # 4. Save TranscriptSegment records into database
            db.execute(
                delete(TranscriptSegment).where(
                    TranscriptSegment.consultation_id == consultation.id
                )
            )
            db.flush()

            db_records: List[TranscriptSegment] = []
            for s in deduped_segments:
                rec = TranscriptSegment(
                    consultation_id=consultation.id,
                    speaker=s["speaker"],
                    text=s["text"],
                    start_time=s["start_time"],
                    end_time=s["end_time"],
                    confidence=0.95,
                )
                db.add(rec)
                db_records.append(rec)

            consultation.stage = "transcribed"
            consultation.status = "processing"
            db.commit()
            for r in db_records:
                db.refresh(r)
            db.refresh(consultation)

            self.timing["final_transcript_completed"] = time.time()

            # 5. Audit logging
            audit_service.log_event(
                db,
                action="AMBIENT_TRANSCRIPTION_COMPLETED",
                user_id=self.doctor_id or consultation.doctor_id,
                consultation_id=consultation.id,
                details={
                    "segment_count": len(db_records),
                    "total_audio_seconds": round(len(self.audio_bytes) / (SAMPLE_RATE * BYTES_PER_SAMPLE), 2),
                    "session_id": self.session_id,
                },
            )

            # Calculate timing metrics
            first_chunk_latency = (
                round(self.timing["first_chunk_received"] - self.timing["capture_start"], 3)
                if self.timing["first_chunk_received"] and self.timing["capture_start"]
                else None
            )
            first_partial_latency = (
                round(self.timing["first_partial_sent"] - self.timing["capture_start"], 3)
                if self.timing["first_partial_sent"] and self.timing["capture_start"]
                else None
            )
            first_final_latency = (
                round(self.timing["first_final_sent"] - self.timing["capture_start"], 3)
                if self.timing["first_final_sent"] and self.timing["capture_start"]
                else None
            )

            logger.info(
                f"Ambient session finalized for consultation {self.consultation_id}: "
                f"{len(db_records)} segments saved. Latency: first_partial={first_partial_latency}s, "
                f"first_final={first_final_latency}s"
            )

            return {
                "consultation_id": self.consultation_id,
                "session_id": self.session_id,
                "segment_count": len(db_records),
                "audio_path": consultation.audio_path,
                "timing_metrics": {
                    "first_chunk_latency_s": first_chunk_latency,
                    "first_partial_latency_s": first_partial_latency,
                    "first_final_latency_s": first_final_latency,
                },
            }


# In-memory registry of active ambient sessions
active_ambient_sessions: Dict[int, AmbientSession] = {}


def get_or_create_ambient_session(consultation_id: int, doctor_id: Optional[int] = None) -> AmbientSession:
    if consultation_id not in active_ambient_sessions:
        active_ambient_sessions[consultation_id] = AmbientSession(consultation_id, doctor_id)
    return active_ambient_sessions[consultation_id]


def remove_ambient_session(consultation_id: int) -> Optional[AmbientSession]:
    return active_ambient_sessions.pop(consultation_id, None)
