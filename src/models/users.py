from sqlalchemy import String, Integer, DateTime, Boolean, text, Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from src.core.database import Base
from src.models.mixin.base_model import BaseMixin


class User(Base, BaseMixin):
    __tablename__ = "users"
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    email_verify_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        server_default=text("true"),
    )
