import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.schemas.auth import LoginRequest, Token, RefreshTokenRequest
from src.schemas.response import APIResponse
from src.crud.users import UserCRUD
from src.core.auth import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
)
from src.utils.email_token import (
    decode_email_otp_token,
    generate_email_otp_token,
    send_otp_email_verification,
    hash_otp,
)
from datetime import datetime, timezone
from src.core.auth import get_current_user
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=APIResponse[Token])
async def login(
    payload: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    user = await UserCRUD.get_user_by_email(db, payload.username)
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user"
        )

    access_token = create_access_token({"user_id": str(user.id)})
    refresh_token = create_refresh_token({"user_id": str(user.id)})
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
    return APIResponse(success=True, message="Login successful", data=token_data)


@router.post("/refresh", response_model=APIResponse[Token])
async def refresh_token(
    payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    data = decode_refresh_token(payload.refresh_token)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user_id = data.get("user_id")
    user = await UserCRUD.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_access_token = create_access_token({"user_id": str(user.id)})
    new_refresh_token = create_refresh_token({"user_id": str(user.id)})
    token_data = {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }
    return APIResponse(success=True, message="Token refreshed successfully", data=token_data)


@router.post("/send-email-otp", response_model=APIResponse[dict])
async def send_email_otp(email: str, db: AsyncSession = Depends(get_db)):
    user = await UserCRUD.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp, token = generate_email_otp_token(email, type="email_verification")

    user.email_verify_token = token
    user.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    await send_otp_email_verification(email, otp)

    return APIResponse(success=True, message="OTP sent to email", data={"email": email})


@router.post("/verify-email-otp", response_model=APIResponse[dict])
async def verify_email_otp(email: str, otp: str, db: AsyncSession = Depends(get_db)):
    user = await UserCRUD.get_user_by_email(db, email)
    if not user or not user.email_verify_token:
        raise HTTPException(
            status_code=404, detail="User not found or Otp has been used "
        )
    try:
        payload = decode_email_otp_token(user.email_verify_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="OTP expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid token")

    if payload["user"] != email:
        raise HTTPException(status_code=400, detail="Token email mismatch")

    if payload["otp"] != hash_otp(otp):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user.email_verify_token = None
    user.is_verified = True
    await db.commit()
    await db.refresh(user)

    return APIResponse(success=True, message="Email verified successfully", data=None)


@router.post("/change-password", response_model=APIResponse[dict])
async def change_password(
    current_password: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = await UserCRUD.get_user_by_id(db, user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(current_password, db_user.password):
        raise HTTPException(status_code=400, detail="Current password incorrect")

    db_user.password = hash_password(new_password)
    db_user.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_user)

    return APIResponse(success=True, message="Password changed successfully", data=None)


@router.post("/forgot-password", response_model=APIResponse[dict])
async def forgot_password(email: str, db: AsyncSession = Depends(get_db)):
    user = await UserCRUD.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp, token = generate_email_otp_token(email, type="password_reset")

    user.email_verify_token = token
    user.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    await send_otp_email_verification(email, otp)

    return APIResponse(success=True, message="Password reset OTP sent", data={"email": email})


@router.post("/reset-password", response_model=APIResponse[dict])
async def reset_password(
    email: str,
    otp: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
):
    user = await UserCRUD.get_user_by_email(db, email)
    if not user or not user.email_verify_token:
        raise HTTPException(status_code=404, detail="Invalid request")

    try:
        payload = decode_email_otp_token(user.email_verify_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="OTP expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid token")

    if payload["user"] != email:
        raise HTTPException(status_code=400, detail="Token email mismatch")

    if payload["otp"] != hash_otp(otp):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user.password = hash_password(new_password)
    user.email_verify_token = None
    user.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    return APIResponse(success=True, message="Password reset successful", data=None)
