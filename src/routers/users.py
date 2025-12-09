from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.crud.users import UserCRUD
from src.schemas.users import UserResponse, UserCreate, UserUpdate
from src.exceptions.user_exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
)
from src.core.auth import hash_password
from uuid import UUID

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user_data = user.model_dump()

        if "password" in user_data:
            user_data["password"] = hash_password(user_data["password"])
        new_user = await UserCRUD.create_user(db, **user_data)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    except UserAlreadyExistsError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception:
        await db.rollback()
        raise


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a user by ID."""
    user = await UserCRUD.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID, payload: UserUpdate, db: AsyncSession = Depends(get_db)
):
    """Update user information."""
    try:
        user_data = payload.model_dump(exclude_unset=True)

        # Hash password if being updated
        if "password" in user_data:
            user_data["password"] = hash_password(user_data["password"])

        updated = await UserCRUD.update_user(db, user_id, **user_data)
        await db.commit()
        await db.refresh(updated)
        return updated
    except UserNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except UserAlreadyExistsError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        await db.rollback()
        raise


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """Soft delete a user."""
    try:
        await UserCRUD.delete_user(db, user_id)
        await db.commit()
        return None
    except UserNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        await db.rollback()
        raise


@router.get("/", response_model=list[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
):
    """List all active users with pagination."""
    return await UserCRUD.list_users(db, skip=skip, limit=limit)
