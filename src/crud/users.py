from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from src.models.users import User
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from src.exceptions.user_exceptions import UserAlreadyExistsError, UserNotFoundError


class UserCRUD:
    ALLOWED_UPDATE_FIELDS = {
        "first_name",
        "last_name",
        "email",
        "phone_number",
    }

    @staticmethod
    async def create_user(db: AsyncSession, **kwargs) -> User:
        try:
            user = User(**kwargs)
            db.add(user)
            await db.flush()
            return user
        except IntegrityError as e:
            await db.rollback()
            if "email" in str(e.orig):
                raise UserAlreadyExistsError("Email already exists")
            elif "phone_number" in str(e.orig):
                raise UserAlreadyExistsError("Phone number already exists")
            raise

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_active)
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.email == email, User.is_active)
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.phone_number == phone, User.is_active)
        )
        return result.scalars().first()

    @staticmethod
    async def update_user(db: AsyncSession, user_id: UUID, **kwargs) -> User:
        filtered_kwargs = {
            k: v for k, v in kwargs.items() if k in UserCRUD.ALLOWED_UPDATE_FIELDS
        }

        if not filtered_kwargs:
            raise ValueError("No valid fields to update")

        stmt = (
            update(User)
            .where(User.id == user_id, User.is_active)
            .values(**filtered_kwargs)
            .returning(User)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundError("User not found")
        if "email" in filtered_kwargs:
            existing = await UserCRUD.get_user_by_email(db, filtered_kwargs["email"])
            if existing and existing.id != user_id:
                raise UserAlreadyExistsError("Email already exists")
        if "phone_number" in filtered_kwargs:
            existing = await UserCRUD.get_user_by_phone(
                db, filtered_kwargs["phone_number"]
            )
            if existing and existing.id != user_id:
                raise UserAlreadyExistsError("Phone number already exists")
        return user

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: UUID) -> bool:
        stmt = (
            update(User)
            .where(User.id == user_id, User.is_active)
            .values(
                is_active=False,
                deleted_at=datetime.now(timezone.utc),
            )
            .returning(User.id)
        )
        result = await db.execute(stmt)

        if not result.scalar_one_or_none():
            raise UserNotFoundError("User not found")

        return True

    @staticmethod
    async def list_users(
        db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[User]:
        result = await db.execute(
            select(User).where(User.is_active).offset(skip).limit(limit)
        )
        return result.scalars().all()
