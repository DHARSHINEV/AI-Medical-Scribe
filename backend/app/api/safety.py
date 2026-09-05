from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.safety import (
    AlertResolveRequest,
    SafetyAlertResponse,
    SafetySummaryResponse,
    SafetyValidationResponse,
)
from app.services import consultation_service, safety_service

router = APIRouter(
    tags=["Safety / Second Look"],
)


@router.get(
    "/api/consultations/{consultation_id}/safety",
    response_model=SafetySummaryResponse,
)
def get_consultation_safety_summary(
    consultation_id: int,
    db: Session = Depends(get_db),
):
    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )

    return safety_service.get_safety_summary(db, consultation_id)


@router.post(
    "/api/consultations/{consultation_id}/validate",
    response_model=List[SafetyAlertResponse],
)
def validate_consultation(
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
        result = safety_service.validate_consultation_safety(
            db=db,
            consultation=consultation,
            user_id=current_user.id if current_user else None,
        )
        return result["alerts"]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Safety validation failed: {exc}",
        ) from exc


@router.get(
    "/api/consultations/{consultation_id}/alerts",
    response_model=List[SafetyAlertResponse],
)
@router.get(
    "/api/consultations/{consultation_id}/safety-alerts",
    response_model=List[SafetyAlertResponse],
)
def get_safety_alerts(
    consultation_id: int,
    db: Session = Depends(get_db),
):
    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )

    return safety_service.get_safety_alerts(db, consultation_id)


@router.post(
    "/api/consultations/{consultation_id}/safety/{alert_id}/resolve",
    response_model=SafetyAlertResponse,
)
def resolve_consultation_alert(
    consultation_id: int,
    alert_id: int,
    resolve_data: Optional[AlertResolveRequest] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    try:
        resolved = resolve_data.resolved if resolve_data else True
        alert = safety_service.resolve_consultation_alert(
            db=db,
            consultation_id=consultation_id,
            alert_id=alert_id,
            user_id=current_user.id if current_user else None,
            resolved=resolved,
        )
        return alert
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            ) from exc
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            ) from exc


@router.post(
    "/api/consultations/{consultation_id}/safety/{alert_id}/unresolve",
    response_model=SafetyAlertResponse,
)
def unresolve_consultation_alert(
    consultation_id: int,
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    try:
        alert = safety_service.resolve_consultation_alert(
            db=db,
            consultation_id=consultation_id,
            alert_id=alert_id,
            user_id=current_user.id if current_user else None,
            resolved=False,
        )
        return alert
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            ) from exc
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            ) from exc


@router.post(
    "/api/alerts/{alert_id}/resolve",
    response_model=SafetyAlertResponse,
)
def resolve_alert(
    alert_id: int,
    resolve_data: Optional[AlertResolveRequest] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    try:
        resolved = resolve_data.resolved if resolve_data else True
        alert = safety_service.resolve_alert(
            db=db,
            alert_id=alert_id,
            user_id=current_user.id if current_user else None,
            resolved=resolved,
        )
        return alert
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
