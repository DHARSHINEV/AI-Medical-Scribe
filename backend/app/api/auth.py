from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.services import audit_service

router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == login_data.email.strip().lower()))
    if not user:
        # For testing/demo convenience, if demo doctor doesn't exist, create it
        if login_data.email.strip().lower() in ("doctor@mediscribe.com", "demo@mediscribe.com"):
            user = User(
                name="Dr. Sarah Jenkins",
                email=login_data.email.strip().lower(),
                password_hash=get_password_hash(login_data.password),
                role="doctor",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
            )

    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )

    audit_service.log_event(
        db,
        action="LOGIN",
        user_id=user.id,
        details={"email": user.email},
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_current_user_profile(
    current_user: User = Depends(require_current_user),
):
    return current_user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(User).where(User.email == user_data.email.strip().lower())
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists.",
        )

    new_user = User(
        name=user_data.name,
        email=user_data.email.strip().lower(),
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
