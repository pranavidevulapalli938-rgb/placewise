from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, index=True)
    email    = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company      = Column(String, nullable=False)
    role         = Column(String, nullable=False)
    status       = Column(String, default="Applied", nullable=False)
    applied_date      = Column(DateTime(timezone=True), default=utcnow)
    gmail_message_id  = Column(String, nullable=True)
    # NEW: stores the job listing URL so user can jump back to the posting
    source_url        = Column(String, nullable=True)

    user           = relationship("User", back_populates="applications")
    notes          = relationship("Note", back_populates="application", cascade="all, delete-orphan")
    status_history = relationship("ApplicationStatusHistory", back_populates="application", cascade="all, delete-orphan")


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id             = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    status         = Column(String, nullable=False)
    timestamp      = Column(DateTime(timezone=True), default=utcnow)

    application = relationship("Application", back_populates="status_history")


class Note(Base):
    __tablename__ = "notes"

    id             = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    text           = Column(Text, nullable=False)
    created_at     = Column(DateTime(timezone=True), default=utcnow)

    application = relationship("Application", back_populates="notes")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token      = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used       = Column(Boolean, default=False, nullable=False)