from pydantic import BaseModel, EmailStr, Field, validator, UUID4
from typing import Optional
import re


class UserCreate(BaseModel):
    first_name: str = Field(..., max_length=100, description="User's first name")
    last_name: str = Field(..., max_length=100, description="User's last name")
    email: EmailStr = Field(..., description="User's email address")
    phone_number: str = Field(
        ..., max_length=15, description="User's phone number with country code"
    )
    password: str = Field(
        ..., min_length=6, description="User's password, minimum 6 characters"
    )

    @validator("phone_number")
    def validate_phone(cls, v):
        pattern = re.compile(r"^\+?\d{7,15}$")
        if not pattern.match(v):
            raise ValueError("Invalid phone number format")
        return v


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, max_length=15)

    @validator("phone_number")
    def validate_phone(cls, v):
        if v is None:
            return v
        pattern = re.compile(r"^\+?\d{7,15}$")
        if not pattern.match(v):
            raise ValueError("Invalid phone number format")
        return v


class UserResponse(BaseModel):
    id: UUID4
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str

    class Config:
        orm_mode = True
