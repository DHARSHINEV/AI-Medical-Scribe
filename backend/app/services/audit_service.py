import logging
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def log_event(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    consultation_id: Optional[int] = None,
    details: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """
    Record an audit log entry in the database.
    Privacy-safe: Avoids persisting raw consultation text.
    """
    try:
        log_entry = AuditLog(
            user_id=user_id,
            consultation_id=consultation_id,
            action=action,
            details=details or {},
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        logger.info(
            f"[AUDIT] Action: {action} | User: {user_id} | Consultation: {consultation_id}"
        )
        return log_entry
    except Exception as exc:
        logger.error(f"Failed to record audit log: {exc}")
        db.rollback()
        raise


def get_consultation_audit_logs(
    db: Session,
    consultation_id: int,
) -> list[AuditLog]:
    """
    Retrieve chronological audit log entries for a consultation.
    """
    from sqlalchemy import select
    statement = (
        select(AuditLog)
        .where(AuditLog.consultation_id == consultation_id)
        .order_by(AuditLog.id.asc())
    )
    return list(db.scalars(statement).all())
