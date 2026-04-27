from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(data: schemas.UserRegister, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = models.User(
        email=data.email,
        password_hash=security.hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.TokenResponse)
def login(data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user or not security.verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    access = security.create_access_token(sub=str(user.id), role=user.role)
    refresh = security.create_refresh_token(sub=str(user.id))

    db.add(models.RefreshToken(
        user_id=user.id,
        token=refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.commit()
    return schemas.TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(data: schemas.RefreshRequest, db: Session = Depends(get_db)):
    payload = security.decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Wrong token type")

    stored = db.query(models.RefreshToken).filter(models.RefreshToken.token == data.refresh_token).first()
    if not stored:
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    user = db.query(models.User).filter(models.User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")

    access = security.create_access_token(sub=str(user.id), role=user.role)
    new_refresh = security.create_refresh_token(sub=str(user.id))

    db.delete(stored)
    db.add(models.RefreshToken(
        user_id=user.id,
        token=new_refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.commit()
    return schemas.TokenResponse(access_token=access, refresh_token=new_refresh)


@router.get("/me", response_model=schemas.UserOut)
def me(current=Depends(security.get_current_user), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == current["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/verify", response_model=schemas.VerifyResponse)
def verify(current=Depends(security.get_current_user)):
    """Internal endpoint for other services to verify a JWT (alternative: decode locally with shared secret)."""
    return schemas.VerifyResponse(user_id=current["user_id"], role=current["role"])
