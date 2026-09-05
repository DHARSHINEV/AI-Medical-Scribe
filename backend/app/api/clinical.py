from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.clinical import ClinicalEntityResponse
from app.services import clinical_service, consultation_service

router = APIRouter(
    prefix="/api/consultations",
    tags=["Clinical NLP"],
)


@router.post(
    "/{consultation_id}/extract",
    response_model=List[ClinicalEntityResponse],
    operation_id="extract_clinical_entities",
)
@router.post(
    "/{consultation_id}/clinical-entities",
    response_model=List[ClinicalEntityResponse],
    include_in_schema=False,
)
def extract_clinical_entities(
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
        entities = clinical_service.extract_clinical_entities(
            db=db,
            consultation=consultation,
            user_id=current_user.id if current_user else None,
        )
        return entities
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clinical extraction failed: {exc}",
        ) from exc


@router.get(
    "/{consultation_id}/clinical_entities",
    response_model=List[ClinicalEntityResponse],
    operation_id="get_clinical_entities",
)
@router.get(
    "/{consultation_id}/clinical-entities",
    response_model=List[ClinicalEntityResponse],
    include_in_schema=False,
)
@router.get(
    "/{consultation_id}/entities",
    response_model=List[ClinicalEntityResponse],
    include_in_schema=False,
)
def get_clinical_entities(
    consultation_id: int,
    db: Session = Depends(get_db),
):
    consultation = consultation_service.get_consultation(db, consultation_id)
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found.",
        )

    return clinical_service.get_clinical_entities(db, consultation_id)
