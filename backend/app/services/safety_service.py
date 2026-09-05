import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.context.history_context import PatientHistoryContext
from app.ai.extraction.entity_extractor import ClinicalEntityExtractor
from app.ai.validation.safety_checker import SafetyChecker
from app.models.clinical_alert import ClinicalAlert
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.models.transcript import TranscriptSegment
from app.services import audit_service, consultation_service

logger = logging.getLogger(__name__)


def validate_consultation_safety(
    db: Session,
    consultation: Consultation,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run Clinical Second Look safety checks on the consultation.
    Compares transcript, extracted entities, and stored patient medical history.
    Retry safety: Replaces previously generated alerts for this consultation.
    """
    segments = list(
        db.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.consultation_id == consultation.id)
            .order_by(TranscriptSegment.start_time.asc())
        ).all()
    )
    if not segments:
        raise ValueError("Cannot run safety checks: consultation transcript is missing.")

    # 1. Update stage
    consultation_service.update_stage(
        db,
        consultation,
        stage="safety_check",
        status="processing",
    )

    try:
        full_transcript = " ".join(s.text for s in segments)

        # 2. Extract clinical entities
        extractor = ClinicalEntityExtractor()
        entities = extractor.extract(full_transcript)

        # 3. Build patient context from database source of truth
        patient = db.get(Patient, consultation.patient_id)
        history_dict = (
            PatientHistoryContext.from_patient_model(patient) if patient else {}
        )
        history_context = PatientHistoryContext().build_context(
            patient_history=history_dict,
            current_entities=entities,
        )

        # 4. Execute Second Look checks
        checker = SafetyChecker()
        safety_result = checker.check(
            transcript=full_transcript,
            entities=entities,
            patient_history_context=history_context,
        )

        # 5. Retry safety: Delete previous unresolved alerts for this consultation
        db.execute(
            delete(ClinicalAlert).where(
                ClinicalAlert.consultation_id == consultation.id,
                ClinicalAlert.resolved == False,
            )
        )
        db.flush()

        # 6. Save ClinicalAlert records
        saved_alerts: List[ClinicalAlert] = []
        for alert_data in safety_result["alerts"]:
            evidence_seg_id = None
            alert_type = alert_data.get("type", "")
            title = alert_data.get("title", "Clinical Verification Notice")
            detail = alert_data.get("detail") or alert_data.get("message", "")

            keywords = [w for w in title.split() if len(w) > 3]
            if alert_type == "allergy_conflict":
                keywords.extend(["allergy", "allergies", "allergic", "penicillin"])
            elif alert_type == "missing_duration":
                keywords.extend(["headache", "fever", "pain", "throat", "cough"])
            elif alert_type == "uncertain_medication":
                keywords.extend(["medication", "medicine", "pill", "tablet", "take"])

            for s in segments:
                if any(kw.lower() in s.text.lower() for kw in keywords):
                    evidence_seg_id = s.id
                    break

            alert = ClinicalAlert(
                consultation_id=consultation.id,
                type=alert_type or "safety_notice",
                title=title,
                detail=detail,
                severity=alert_data.get("severity", "Medium"),
                evidence_segment_id=evidence_seg_id,
                requires_review=alert_data.get("requires_review", True),
                resolved=False,
            )
            db.add(alert)
            saved_alerts.append(alert)

        db.commit()
        for a in saved_alerts:
            db.refresh(a)

        # 7. Update stage to review (review-ready)
        consultation_service.update_stage(
            db,
            consultation,
            stage="review",
            status="review",
        )

        for a in saved_alerts:
            audit_service.log_event(
                db,
                action="ALERT_CREATED",
                user_id=user_id or consultation.doctor_id,
                consultation_id=consultation.id,
                details={
                    "alert_id": a.id,
                    "type": a.type,
                    "severity": a.severity,
                },
            )

        return {
            "consultation_id": consultation.id,
            "alerts": saved_alerts,
            "alert_count": len(saved_alerts),
            "high_priority_alert_count": safety_result["high_priority_alert_count"],
            "review_required": safety_result["review_required"],
        }

    except Exception as exc:
        db.rollback()
        consultation_service.update_stage(
            db,
            consultation,
            stage="error",
            status="failed",
        )
        logger.error(f"Safety check failed for consultation {consultation.id}: {exc}")
        raise


def get_safety_alerts(
    db: Session,
    consultation_id: int,
) -> List[ClinicalAlert]:
    statement = (
        select(ClinicalAlert)
        .where(ClinicalAlert.consultation_id == consultation_id)
        .order_by(ClinicalAlert.id.asc())
    )
    return list(db.scalars(statement).all())


def get_safety_summary(
    db: Session,
    consultation_id: int,
) -> Dict[str, Any]:
    alerts = get_safety_alerts(db, consultation_id)
    alert_count = len(alerts)
    high_priority_alert_count = len([
        a for a in alerts if a.severity.lower() == "high" and not a.resolved
    ])
    # Conceptually: review_required = at least one unresolved alert where requires_review = true
    review_required = any(a.requires_review and not a.resolved for a in alerts)

    return {
        "consultation_id": consultation_id,
        "review_required": review_required,
        "alert_count": alert_count,
        "high_priority_alert_count": high_priority_alert_count,
        "alerts": alerts,
    }


def resolve_consultation_alert(
    db: Session,
    consultation_id: int,
    alert_id: int,
    user_id: Optional[int] = None,
    resolved: bool = True,
) -> ClinicalAlert:
    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise ValueError(f"Consultation with id {consultation_id} not found.")

    alert = db.get(ClinicalAlert, alert_id)
    if not alert:
        raise ValueError(f"Alert with id {alert_id} not found.")

    if alert.consultation_id != consultation_id:
        raise ValueError(
            f"Alert with id {alert_id} does not belong to consultation {consultation_id}."
        )

    was_already_resolved = alert.resolved == resolved
    alert.resolved = resolved
    db.commit()
    db.refresh(alert)

    action = "SAFETY_ALERT_RESOLVED" if resolved else "SAFETY_ALERT_UNRESOLVED"
    audit_service.log_event(
        db,
        action=action,
        user_id=user_id or consultation.doctor_id,
        consultation_id=consultation.id,
        details={
            "alert_id": alert.id,
            "resolved": resolved,
            "idempotent": was_already_resolved,
        },
    )

    return alert


def resolve_alert(
    db: Session,
    alert_id: int,
    user_id: Optional[int] = None,
    resolved: bool = True,
) -> ClinicalAlert:
    alert = db.get(ClinicalAlert, alert_id)
    if not alert:
        raise ValueError(f"Alert with id {alert_id} not found.")

    was_already_resolved = alert.resolved == resolved
    alert.resolved = resolved
    db.commit()
    db.refresh(alert)

    action = "SAFETY_ALERT_RESOLVED" if resolved else "SAFETY_ALERT_UNRESOLVED"
    audit_service.log_event(
        db,
        action=action,
        user_id=user_id,
        consultation_id=alert.consultation_id,
        details={
            "alert_id": alert.id,
            "resolved": resolved,
            "idempotent": was_already_resolved,
        },
    )

    return alert
