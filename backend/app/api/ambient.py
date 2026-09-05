import base64
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.database import SessionLocal
from app.models.consultation import Consultation
from app.models.user import User
from app.services.ambient_service import (
    get_or_create_ambient_session,
    remove_ambient_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Ambient Clinical Documentation / Realtime"],
)


def get_websocket_db() -> Session:
    """Helper to instantiate DB session respecting test overrides if present."""
    from app.main import app
    from app.core.dependencies import get_db

    if get_db in app.dependency_overrides:
        override = app.dependency_overrides[get_db]
        gen = override()
        if hasattr(gen, "__next__"):
            return next(gen)
        return gen()
    return SessionLocal()


async def handle_ambient_websocket(websocket: WebSocket, consultation_id: int):
    """
    Core WebSocket handler for Ambient Clinical Documentation.
    Accepts real-time PCM16 audio chunks, streams Faster-Whisper transcripts,
    and finalizes session into consultation records.
    """
    db: Session = get_websocket_db()

    try:

        # 1. Authenticate WebSocket connection via token query param or header
        token: Optional[str] = websocket.query_params.get("token")
        if not token:
            auth_header = websocket.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]

        if not token:
            logger.warning("Ambient WebSocket connection rejected: Missing token")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        payload = decode_access_token(token)
        if not payload or not payload.get("sub"):
            logger.warning("Ambient WebSocket connection rejected: Invalid/expired token")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user_id = int(payload["sub"])
        user = db.get(User, user_id)
        if not user:
            logger.warning(f"Ambient WebSocket rejected: User {user_id} not found")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 2. Validate Consultation access
        consultation = db.get(Consultation, consultation_id)
        if not consultation:
            logger.warning(f"Ambient WebSocket rejected: Consultation {consultation_id} not found")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Clinician ownership check (allow owner or admin)
        if consultation.doctor_id and consultation.doctor_id != user.id and user.role != "admin":
            logger.warning(
                f"Ambient WebSocket rejected: Doctor {user.id} unauthorized for consultation {consultation_id}"
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Auth & validation passed -> Accept connection
        await websocket.accept()


        # 3. Initialize Ambient Session
        session = get_or_create_ambient_session(consultation_id, doctor_id=user.id)
        logger.info(
            f"Ambient session {session.session_id} connected for consultation {consultation_id} by user {user.id}"
        )

        await websocket.send_json(
            {
                "type": "connected",
                "consultation_id": consultation_id,
                "session_id": session.session_id,
                "sample_rate": 16000,
                "channels": 1,
                "format": "PCM16",
            }
        )

        # 4. Message Pump Loop
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"]:
                # Binary PCM16 audio chunk received
                session.append_pcm16_chunk(message["bytes"])
                events = await session.process_incremental()
                for evt in events:
                    await websocket.send_json(evt)

            elif "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                except Exception:
                    data = {"type": message["text"]}

                msg_type = data.get("type", "").lower()

                if msg_type == "audio":
                    # Base64 encoded audio payload
                    b64_data = data.get("data", "")
                    if b64_data:
                        raw_bytes = base64.b64decode(b64_data)
                        session.append_pcm16_chunk(raw_bytes)
                        events = await session.process_incremental()
                        for evt in events:
                            await websocket.send_json(evt)

                elif msg_type == "pause":
                    session.is_paused = True
                    await websocket.send_json({"type": "processing", "stage": "paused"})

                elif msg_type == "resume":
                    session.is_paused = False
                    await websocket.send_json({"type": "processing", "stage": "recording"})

                elif msg_type in ("stop", "finalize"):
                    await websocket.send_json({"type": "finalizing"})
                    final_result = await session.finalize_session(db, consultation)
                    await websocket.send_json(
                        {
                            "type": "completed",
                            "consultation_id": consultation_id,
                            "segment_count": final_result["segment_count"],
                            "audio_path": final_result["audio_path"],
                            "timing_metrics": final_result["timing_metrics"],
                        }
                    )
                    break

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "reset":
                    remove_ambient_session(consultation_id)
                    session = get_or_create_ambient_session(consultation_id, doctor_id=user.id)
                    await websocket.send_json({"type": "processing", "stage": "reset"})

    except WebSocketDisconnect:
        logger.info(f"Ambient WebSocket disconnected for consultation {consultation_id}")
    except Exception as exc:
        logger.error(f"Unhandled error in ambient WebSocket: {exc}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": f"Server error: {exc}"})
        except Exception:
            pass
    finally:
        remove_ambient_session(consultation_id)
        from app.core.dependencies import get_db
        from app.main import app
        if get_db not in app.dependency_overrides:
            db.close()



@router.websocket("/ws/consultations/{consultation_id}/ambient")
async def ws_consultation_ambient(websocket: WebSocket, consultation_id: int):
    await handle_ambient_websocket(websocket, consultation_id)


@router.websocket("/api/ws/consultations/{consultation_id}/ambient")
async def api_ws_consultation_ambient(websocket: WebSocket, consultation_id: int):
    await handle_ambient_websocket(websocket, consultation_id)
