from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.db.database import SessionLocal
from backend.db.models import User
from backend.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserOut
from backend.security import create_access_token

try:
    from passlib.context import CryptContext
except ImportError as exc:  # pragma: no cover
    raise RuntimeError('passlib is required for password hashing') from exc

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest):
    normalized_email = payload.email.strip().lower()
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name cannot be empty")

    if not normalized_email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email is required")

    if len(payload.password.strip()) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters long")

    db: Session = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == normalized_email))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        user = User(
            name=name,
            email=normalized_email,
            password_hash=pwd_context.hash(payload.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return UserOut.model_validate(user)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User registration failed") from exc
    finally:
        db.close()


@router.post("/login", status_code=status.HTTP_200_OK)
def login_user(payload: LoginRequest):
    normalized_email = payload.email.strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email is required")

    if len(payload.password.strip()) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters long")

    db: Session = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        if not pwd_context.verify(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        token = create_access_token(str(user.id))
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
            },
        }
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed") from exc
    finally:
        db.close()
