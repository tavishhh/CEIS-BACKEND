import re
import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CareerRoleBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=140)
    department: str = Field(..., min_length=2, max_length=80)
    location: str = Field(default="Indore, MP (On-Site / Hybrid)", max_length=120)
    employment_type: str = Field(default="Full-Time", max_length=50)
    experience: str | None = Field(None, max_length=60)
    description: str = Field(..., min_length=10)
    is_active: bool = True

    @field_validator("title", "department", "location", "employment_type", mode="before")
    @classmethod
    def strip_text_fields(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Description must be a string.")
        val = v.strip()
        if len(val) < 10:
            raise ValueError("Role description must be at least 10 characters.")
        return val


class CareerRoleCreate(CareerRoleBase):
    model_config = ConfigDict(extra="forbid")


class CareerRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    department: str | None = None
    location: str | None = None
    employment_type: str | None = None
    experience: str | None = None
    description: str | None = None
    is_active: bool | None = None


class CareerRoleResponse(CareerRoleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class JobApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: uuid.UUID | None = None
    role_title: str = Field(..., min_length=2, max_length=140)
    full_name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr = Field(..., max_length=160)
    phone: str = Field(..., min_length=7, max_length=30)
    portfolio_url: str = Field(..., min_length=10)
    resume_url: str = Field(..., min_length=10)
    cover_note: str | None = Field(None, max_length=1500)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Full name must be a string.")
        val = v.strip()
        if len(val) < 2 or len(val) > 80:
            raise ValueError("Full name must be between 2 and 80 characters.")
        if re.search(r"\d", val):
            raise ValueError("Full name cannot contain numbers or digits.")
        stripped = re.sub(r"[\s.'-]", "", val)
        if not stripped or not stripped.isalpha():
            raise ValueError("Full name can only contain letters, spaces, hyphens, periods, and apostrophes.")
        return val

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip().lower()
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Phone number must be a string.")
        val = v.strip()
        if re.search(r"[a-zA-Z]", val):
            raise ValueError("Phone number cannot contain letters.")
        if not re.match(r"^[\d\s+\-()]{7,30}$", val):
            raise ValueError("Phone number contains invalid characters.")
        digits = re.sub(r"\D", "", val)
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError("Phone number must contain between 7 and 15 digits.")
        return val

    @field_validator("portfolio_url", "resume_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("URL must be a string.")
        val = v.strip()
        if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", val, re.IGNORECASE):
            raise ValueError("URL must start with http:// or https:// and be a valid web address.")
        return val

    @field_validator("cover_note")
    @classmethod
    def validate_cover_note(cls, v: str | None) -> str | None:
        if v is None:
            return None
        val = v.strip()
        if not val:
            return None
        if re.search(r"<\s*script[^>]*>", val, re.IGNORECASE) or re.search(r"javascript\s*:", val, re.IGNORECASE):
            raise ValueError("Cover note contains disallowed script content.")
        clean_val = re.sub(r"<[^>]*>", "", val).strip()
        if len(clean_val) > 1500:
            raise ValueError("Cover note cannot exceed 1500 characters.")
        return clean_val


class JobApplicationCreateResponse(BaseModel):
    application_id: str
    status: str


class JobApplicationStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: Literal["received", "shortlisted", "interviewing", "reviewed", "in_review", "rejected", "hired", "archived"]


class JobApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: str
    role_id: uuid.UUID | None = None
    role_title: str
    full_name: str
    email: str
    phone: str
    portfolio_url: str
    resume_url: str
    cover_note: str | None = None
    status: str
    created_at: datetime
