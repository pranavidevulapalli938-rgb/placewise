from pydantic import BaseModel, EmailStr, Field

# --------- REQUEST SCHEMA ---------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)


# --------- RESPONSE SCHEMA ---------
class UserResponse(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True
        
        
# Login request schema
class UserLogin(BaseModel):
    email: EmailStr
    password: str


#Application create

class ApplicationCreate(BaseModel):
    company: str
    role: str


# ---------- APPLICATION RESPONSE ----------
class ApplicationResponse(BaseModel):
    id: int
    company: str
    role: str
    status: str

    class Config:
        from_attributes = True


# ---------- STATUS UPDATE ----------
class StatusUpdate(BaseModel):
    status: str


# ---------- NOTE CREATE ----------
class NoteCreate(BaseModel):
    text: str


class CodePayload(BaseModel):
    language: str
    code: str

