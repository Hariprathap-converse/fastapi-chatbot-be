from passlib.hash import argon2
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.crud.users import UserCRUD
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Environment variables with validation
SECRET_KEY = os.getenv("SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")

if not SECRET_KEY or not REFRESH_SECRET_KEY:
    raise ValueError(
        "SECRET_KEY and REFRESH_SECRET_KEY must be set in environment variables"
    )

if len(SECRET_KEY) < 32 or len(REFRESH_SECRET_KEY) < 32:
    raise ValueError("Secret keys must be at least 32 characters long")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 90
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Password hashing using argon2
def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return argon2.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return argon2.verify(plain_password, hashed_password)


# JWT creation
def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update(
        {"exp": expire, "type": "access", "iat": datetime.now(timezone.utc).timestamp()}
    )
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
            "iat": datetime.now(timezone.utc).timestamp(),
        }
    )
    return jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)


# JWT decoding
def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate an access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    """Decode and validate a refresh token."""
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    """
    Dependency to get the current authenticated user from JWT token.
    Raises 401 if token is invalid or user is not found/inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id = payload.get("user_id")
    if not user_id:
        raise credentials_exception

    user = await UserCRUD.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise credentials_exception

    return user


async def get_current_active_user(current_user=Depends(get_current_user)):
    """
    Dependency to ensure user is active.
    (Already checked in get_current_user, but kept for clarity)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return current_user
