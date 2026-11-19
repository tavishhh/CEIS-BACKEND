import re
import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ClientInquiryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr = Field(..., max_length=160)
    company: str | None = Field(None, max_length=160)
    service_interest: str | None = Field(None, max_length=100)
    message: str = Field(..., min_length=10, max_length=2000)

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

    @field_validator("company")
    @classmethod
    def validate_company(cls, v: str | None) -> str | None:
        if v is None:
            return None
        val = v.strip()
        if not val:
            return None
        if len(re.findall(r"[a-zA-Z0-9]", val)) < 2:
            raise ValueError("Company name must contain at least 2 alphanumeric characters.")
        if len(val) > 160:
            raise ValueError("Company name cannot exceed 160 characters.")
        return val

    @field_validator("service_interest")
    @classmethod
    def sanitize_service_interest(cls, v: str | None) -> str | None:
        if v is None:
            return None
        val = v.strip()
        return val if val else None

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Message must be a string.")
        val = v.strip()
        if re.search(r"<\s*script[^>]*>", val, re.IGNORECASE) or re.search(r"javascript\s*:", val, re.IGNORECASE):
            raise ValueError("Message contains disallowed script or executable content.")
        clean_val = re.sub(r"<[^>]*>", "", val).strip()
        if len(clean_val) < 10:
            raise ValueError("Project requirements message must be at least 10 characters.")
        if len(clean_val) > 2000:
            raise ValueError("Project requirements message cannot exceed 2000 characters.")
        return clean_val


class ClientInquiryCreateResponse(BaseModel):
    reference_id: str
    status: str
    created_at: datetime


class ClientInquiryStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["new", "in_review", "contacted", "archived"]


class ClientInquiryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference_id: str
    full_name: str
    email: str
    company: str | None = None
    service_interest: str | None = None
    message: str
    status: str
    created_at: datetime
