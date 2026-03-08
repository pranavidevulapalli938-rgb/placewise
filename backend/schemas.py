from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class UserResponse(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ApplicationStatus(str, Enum):
    applied             = "Applied"
    oa_received         = "OA Received"
    interview_scheduled = "Interview Scheduled"
    selected            = "Selected"
    rejected            = "Rejected"


class ApplicationCreate(BaseModel):
    company:    str = Field(..., min_length=1, max_length=200)
    role:       str = Field(..., min_length=1, max_length=200)
    source_url: Optional[str] = None   # job listing URL (LinkedIn, Naukri, etc.)


class ApplicationResponse(BaseModel):
    id:               int
    company:          str
    role:             str
    status:           str
    applied_date:     Optional[datetime] = None
    gmail_message_id: Optional[str] = None
    source_url:       Optional[str] = None  # NEW

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: ApplicationStatus


class NoteCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class NoteResponse(BaseModel):
    id:         int
    text:       str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SupportedLanguage(str, Enum):
    python = "python"
    java   = "java"


class CodePayload(BaseModel):
    language: SupportedLanguage
    code:     str = Field(..., max_length=10_000)


# ── Password Reset ────────────────────────────────────────────────────────────
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token:        str
    new_password: str = Field(..., min_length=8, max_length=100)