import sys
import shutil
import subprocess
import tempfile
import os
import secrets
import smtplib
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

from database import engine, SessionLocal
from models import Base, User, Application, ApplicationStatusHistory, Note, PasswordResetToken
from schemas import (
    UserCreate, UserResponse, UserLogin,
    ApplicationCreate, ApplicationResponse,
    StatusUpdate, NoteCreate, CodePayload,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from auth import hash_password, verify_password, create_access_token, decode_access_token
from gmail_parser import get_flow, fetch_and_parse_placement_emails

# ──────────────────────────────────────────
# ENVIRONMENT & CONFIG
# ──────────────────────────────────────────

load_dotenv()

# Only allow insecure transport in development (not production)
if os.getenv("ENVIRONMENT", "development") == "development":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# ── Cross-platform executable detection ──────────────────────────────────────
PYTHON_PATH = sys.executable
JAVA_PATH   = shutil.which("java")
JAVAC_PATH  = shutil.which("javac")

# ──────────────────────────────────────────
# GMAIL TOKEN MODEL  (persisted to DB)
# ──────────────────────────────────────────

class GmailToken(Base):
    __tablename__ = "gmail_tokens"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    token         = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)

# NOTE: pending_oauth dict removed — it was in-memory and wiped on every
# Render spin-down, causing "invalid_grant: Invalid code verifier" errors.
# PKCE is optional for server-side OAuth and has been removed entirely.

# ──────────────────────────────────────────
# APP SETUP
# ──────────────────────────────────────────

app = FastAPI(
    title="Placement Tracker API",
    version="1.0.0",
    description="Backend for university placement tracking system"
)

# FIX: Chrome extensions cannot use wildcard origin matching like "chrome-extension://*"
# The correct fix is to allow ALL origins with allow_origins=["*"]
# and handle auth via Bearer token (not cookies), so allow_credentials must be False.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://placewise-azure.vercel.app"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create all DB tables on startup (including the new gmail_tokens table)
Base.metadata.create_all(bind=engine)

security = HTTPBearer()


# ──────────────────────────────────────────
# DEPENDENCIES
# ──────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(auth: HTTPAuthorizationCredentials = Depends(security)) -> int:
    payload = decode_access_token(auth.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload.get("user_id")


# ──────────────────────────────────────────
# ROOT
# ──────────────────────────────────────────

@app.get("/", tags=["Health"])
def read_root():
    return {"status": "InterviewAI backend running ✅", "version": "1.0.0"}


@app.get("/me", tags=["Auth"])
def get_me(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Returns current user's email (used for avatar initials)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "email": user.email}


# ──────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────

@app.post("/register", response_model=UserResponse, tags=["Auth"])
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(email=user.email, password=hash_password(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/login", tags=["Auth"])
@app.post("/auth/login", tags=["Auth"])
def login(user: UserLogin, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if not existing_user or not verify_password(user.password, existing_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"user_id": existing_user.id})

    return {"access_token": token, "token_type": "bearer"}


# ── Password Reset helpers ────────────────────────────────────────────────────

def send_reset_email(to_email: str, reset_link: str):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_user or not smtp_pass:
        print(f"[EMAIL] SMTP not configured — reset link: {reset_link}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your PlaceWise password"
    msg["From"]    = smtp_from
    msg["To"]      = to_email

    text_body = f"""Hi,

You requested a password reset for your PlaceWise account.
Click the link below to set a new password (valid for 30 minutes):

{reset_link}

If you didn't request this, you can safely ignore this email.

— The PlaceWise Team
"""
    html_body = f"""
<html><body style="font-family:sans-serif;background:#0f1117;color:#fff;padding:40px;">
  <div style="max-width:480px;margin:auto;background:#13151f;border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:40px;">
    <h2 style="color:#a78bfa;margin-bottom:8px;">Reset your password</h2>
    <p style="color:rgba(255,255,255,0.6);font-size:14px;margin-bottom:28px;">
      You requested a password reset for your PlaceWise account. This link expires in 30 minutes.
    </p>
    <a href="{reset_link}"
       style="display:inline-block;background:linear-gradient(to right,#7c3aed,#4f46e5);color:#fff;
              text-decoration:none;padding:14px 28px;border-radius:12px;font-weight:600;font-size:15px;">
      Reset Password
    </a>
    <p style="color:rgba(255,255,255,0.3);font-size:12px;margin-top:28px;">
      If you didn't request this, ignore this email — your password won't change.
    </p>
  </div>
</body></html>
"""
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # FIX: added timeout=10 so a bad SMTP config fails fast instead of hanging forever
    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, to_email, msg.as_string())
    print(f"[EMAIL] Reset email sent to {to_email}")


@app.post("/auth/forgot-password", tags=["Auth"])
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Always returns 200 to prevent email enumeration."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        return {"message": "If that email is registered, a reset link has been sent."}

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False
    ).delete()
    db.commit()

    token_str = secrets.token_urlsafe(48)
    expires   = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.add(PasswordResetToken(user_id=user.id, token=token_str, expires_at=expires))
    db.commit()

    reset_link = f"{FRONTEND_URL}/reset-password?token={token_str}"
    try:
        send_reset_email(user.email, reset_link)
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")

    return {"message": "If that email is registered, a reset link has been sent."}


@app.get("/auth/verify-reset-token", tags=["Auth"])
def verify_reset_token(token: str, db: Session = Depends(get_db)):
    row = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.used == False
    ).first()
    if not row or row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return {"valid": True}


@app.post("/auth/reset-password", tags=["Auth"])
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    row = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == req.token,
        PasswordResetToken.used == False
    ).first()
    if not row or row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password = hash_password(req.new_password)
    row.used = True
    db.commit()
    return {"message": "Password reset successfully"}


# ──────────────────────────────────────────
# APPLICATIONS
# ──────────────────────────────────────────

@app.post("/applications", tags=["Applications"])
def add_application(
    app_data: ApplicationCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    existing = db.query(Application).filter(
        Application.user_id == user_id,
        Application.company == app_data.company,
        Application.role == app_data.role
    ).first()

    if existing:
        return {"message": "already_exists", "id": existing.id}

    new_app = Application(
        user_id=user_id,
        company=app_data.company,
        role=app_data.role,
        source_url=app_data.source_url,
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)
    return {"message": "created", "id": new_app.id}


@app.get("/applications", tags=["Applications"])
def get_applications(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    apps = db.query(Application).filter(Application.user_id == user_id).all()
    return apps


@app.patch("/applications/{app_id}/status", tags=["Applications"])
def update_status(
    app_id: int,
    status_data: StatusUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == user_id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    VALID_STATUSES = {"Applied", "OA Received", "Interview Scheduled", "Selected", "Rejected"}
    if status_data.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {VALID_STATUSES}")

    app.status = status_data.status
    db.add(ApplicationStatusHistory(application_id=app.id, status=status_data.status))
    db.commit()
    return {"message": "Status updated successfully"}


@app.delete("/applications/{app_id}", tags=["Applications"])
def delete_application(
    app_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == user_id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    db.delete(app)
    db.commit()
    return {"message": "Application deleted"}


# ──────────────────────────────────────────
# NOTES
# ──────────────────────────────────────────

@app.post("/applications/{app_id}/notes", tags=["Notes"])
def add_note(
    app_id: int,
    note: NoteCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == user_id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    new_note = Note(application_id=app_id, text=note.text)
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return {"message": "Note added", "id": new_note.id}


@app.get("/applications/{app_id}/notes", tags=["Notes"])
def get_notes(
    app_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == user_id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    return db.query(Note).filter(Note.application_id == app_id).all()


@app.delete("/applications/{app_id}/notes/{note_id}", tags=["Notes"])
def delete_note(
    app_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == user_id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    note = db.query(Note).filter(Note.id == note_id, Note.application_id == app_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()
    return {"message": "Note deleted"}


# ──────────────────────────────────────────
# GMAIL OAUTH
# ──────────────────────────────────────────

def _get_gmail_token_row(user_id: int, db: Session):
    return db.query(GmailToken).filter(GmailToken.user_id == user_id).first()


def _is_token_expired_error(err_str: str) -> bool:
    err_lower = err_str.lower()
    return any(x in err_lower for x in [
        "invalid_grant", "token has been expired", "token has been revoked",
        "revoked", "reauth", "refresh", "unauthorized",
        "invalid credentials", "access_denied",
    ])


@app.get("/gmail/connect", tags=["Gmail"])
def gmail_connect(user_id: int = Depends(get_current_user_id)):
    # FIX: removed PKCE (code_verifier) — it was stored in-memory via pending_oauth
    # dict which gets wiped on every Render spin-down, causing "invalid_grant:
    # Invalid code verifier" errors. PKCE is optional for server-side OAuth flows.
    flow = get_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=str(user_id)
    )
    return {"auth_url": auth_url}


@app.get("/gmail/callback", tags=["Gmail"])
def gmail_callback(code: str, state: str):
    # FIX: removed pending_oauth.pop() and flow.code_verifier — no longer using PKCE
    db = SessionLocal()
    try:
        user_id = int(state)
        flow = get_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        existing = db.query(GmailToken).filter(GmailToken.user_id == user_id).first()
        if existing:
            existing.token         = creds.token
            existing.refresh_token = creds.refresh_token
        else:
            db.add(GmailToken(
                user_id=user_id,
                token=creds.token,
                refresh_token=creds.refresh_token,
            ))
        db.commit()
        return RedirectResponse(f"{FRONTEND_URL}/dashboard?gmail=connected")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gmail OAuth failed: {str(e)}")
    finally:
        db.close()


@app.get("/gmail/status", tags=["Gmail"])
def gmail_status(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    # FIX: only report connected if we actually have a refresh token stored.
    # Previously this returned connected=true even after token expiry/deletion,
    # causing the dashboard to show "Sync Gmail" instead of "Connect Gmail".
    row = _get_gmail_token_row(user_id, db)
    connected = row is not None and bool(row.refresh_token)
    return {"gmail_connected": connected}


@app.post("/gmail/sync", tags=["Gmail"])
def gmail_sync(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    token_row = _get_gmail_token_row(user_id, db)
    if not token_row:
        raise HTTPException(status_code=400, detail="Gmail not connected. Visit /gmail/connect first.")

    if not token_row.refresh_token:
        db.delete(token_row)
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Gmail token is incomplete (no refresh token). Please reconnect Gmail."
        )

    tokens = {"token": token_row.token, "refresh_token": token_row.refresh_token}
    seen_ids: set[str] = {
        row.gmail_message_id
        for row in db.query(Application.gmail_message_id)
                     .filter(Application.user_id == user_id, Application.gmail_message_id.isnot(None))
                     .all()
    }

    try:
        emails = fetch_and_parse_placement_emails(tokens, seen_message_ids=seen_ids)
    except Exception as e:
        err_str = str(e)
        print(f"[gmail_sync ERROR] user_id={user_id}")
        print(traceback.format_exc())
        if _is_token_expired_error(err_str):
            db.delete(token_row)
            db.commit()
            raise HTTPException(status_code=401, detail="Gmail token expired or revoked. Please reconnect Gmail.")
        raise HTTPException(status_code=500, detail=f"Gmail fetch failed: {err_str}")

    created, updated, skipped, cleaned = 0, 0, 0, 0
    STATUS_RANK = {"Applied": 0, "OA Received": 1, "Interview Scheduled": 2, "Rejected": 3, "Selected": 4}

    DEFINITE_JUNK = {
        "jobalert", "job alert", "job alerts", "jobalerts",
        "linkedin job alerts", "linkedin jobs",
        "indeed apply", "indeedapply", "unstop events",
        "recooty", "naukricampus", "dare2compete",
        "job digest", "job alert digest",
    }
    all_gmail_apps = db.query(Application).filter(
        Application.user_id == user_id, Application.role == "(via Gmail)", Application.status == "Applied"
    ).all()
    for app in all_gmail_apps:
        if app.company.lower().strip() in DEFINITE_JUNK:
            db.delete(app)
            cleaned += 1
    if cleaned:
        db.commit()

    import re as _re
    best_per_company: dict = {}
    for email in emails:
        company = email.get("company")
        status  = email.get("status")
        if not company or not status:
            skipped += 1
            continue
        role = email.get("role") or "(via Gmail)"
        key = (company.lower(), role.lower())
        current_rank = STATUS_RANK.get(status, -1)
        existing_best = best_per_company.get(key)
        if existing_best is None or current_rank > STATUS_RANK.get(existing_best["status"], -1):
            best_per_company[key] = {
                "company": company, "status": status, "role": role,
                "email_date": email.get("email_date"),
                "gmail_message_id": email.get("gmail_message_id"),
            }

    for key, best in best_per_company.items():
        company = best["company"]; status = best["status"]
        role = best["role"]; email_date = best["email_date"]

        existing = db.query(Application).filter(
            Application.user_id == user_id, Application.company.ilike(company)
        ).first()

        if not existing:
            company_prefix = company.rstrip("., ").lower()
            for a in db.query(Application).filter(Application.user_id == user_id).all():
                db_prefix = a.company.rstrip("., ").lower()
                if db_prefix == company_prefix or (
                    db_prefix.startswith(company_prefix[:20]) and abs(len(db_prefix) - len(company_prefix)) <= 5
                ):
                    existing = a
                    break

        if existing:
            new_rank = STATUS_RANK.get(status, -1)
            cur_rank = STATUS_RANK.get(existing.status, -1)
            if new_rank > cur_rank:
                existing.status = status
                if not existing.applied_date and email_date:
                    existing.applied_date = email_date
                db.add(ApplicationStatusHistory(application_id=existing.id, status=status))
                updated += 1
            else:
                skipped += 1
        else:
            new_app = Application(
                user_id=user_id, company=company, role=role, status=status,
                applied_date=email_date, gmail_message_id=best.get("gmail_message_id"),
            )
            db.add(new_app)
            db.flush()
            db.add(ApplicationStatusHistory(application_id=new_app.id, status=status))
            created += 1

    db.commit()
    return {
        "message": "Gmail sync complete", "created": created, "updated": updated,
        "skipped": skipped, "cleaned": cleaned, "total_emails_parsed": len(emails)
    }


@app.get("/gmail/debug", tags=["Gmail"])
def gmail_debug(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    token_row = _get_gmail_token_row(user_id, db)
    if not token_row:
        raise HTTPException(status_code=400, detail="Gmail not connected.")
    try:
        emails = fetch_and_parse_placement_emails(
            {"token": token_row.token, "refresh_token": token_row.refresh_token}
        )
    except Exception as e:
        err_str = str(e)
        print(traceback.format_exc())
        if _is_token_expired_error(err_str):
            db.delete(token_row); db.commit()
            raise HTTPException(status_code=401, detail="Gmail token expired or revoked.")
        raise HTTPException(status_code=500, detail=f"Gmail fetch failed: {err_str}")

    STATUS_RANK = {"Applied": 0, "OA Received": 1, "Interview Scheduled": 2, "Rejected": 3, "Selected": 4}
    best_per_company = {}
    for email in emails:
        company = email.get("company"); status = email.get("status")
        if not company or not status: continue
        key = company.lower()
        if key not in best_per_company or STATUS_RANK.get(status, -1) > STATUS_RANK.get(best_per_company[key]["status"], -1):
            best_per_company[key] = {"company": company, "status": status, "subject": email.get("subject", "")[:80]}

    results = []
    for key, best in best_per_company.items():
        existing = db.query(Application).filter(
            Application.user_id == user_id, Application.company.ilike(best["company"])
        ).first()
        results.append({
            "email_company": best["company"], "email_status": best["status"],
            "subject_preview": best["subject"],
            "db_match": existing.company if existing else None,
            "db_status": existing.status if existing else None,
            "would_update": (STATUS_RANK.get(best["status"], -1) > STATUS_RANK.get(existing.status if existing else "Applied", -1)) if existing else "would_create"
        })

    return {"total_parsed": len(emails), "unique_companies": len(best_per_company), "breakdown": sorted(results, key=lambda x: x["email_status"])}


@app.delete("/gmail/disconnect", tags=["Gmail"])
def gmail_disconnect(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    row = _get_gmail_token_row(user_id, db)
    if row:
        db.delete(row); db.commit()
    return {"message": "Gmail disconnected"}


@app.delete("/gmail/reset", tags=["Gmail"])
def gmail_reset(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    deleted = db.query(Application).filter(Application.user_id == user_id, Application.role == "(via Gmail)").all()
    count = len(deleted)
    for app in deleted: db.delete(app)
    db.commit()
    return {"message": f"Deleted {count} Gmail-imported applications. Now click Sync Gmail."}


@app.delete("/gmail/reset-all", tags=["Gmail"])
def gmail_reset_all(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    gmail_apps = db.query(Application).filter(Application.user_id == user_id, Application.role == "(via Gmail)").all()
    count = len(gmail_apps)
    for app in gmail_apps: db.delete(app)
    db.commit()
    return {"message": f"Hard reset complete. Deleted {count} Gmail apps. Now Sync Gmail again.", "deleted": count}


@app.delete("/gmail/remove-company/{company_name}", tags=["Gmail"])
def gmail_remove_company(company_name: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    apps = db.query(Application).filter(Application.user_id == user_id, Application.company.ilike(company_name)).all()
    count = len(apps)
    for app in apps: db.delete(app)
    db.commit()
    return {"message": f"Deleted {count} application(s) for '{company_name}'."}


# ──────────────────────────────────────────
# CODE EXECUTION  (sandboxed)
# ──────────────────────────────────────────

@app.post("/execute", tags=["Code Execution"])
def execute_code(payload: CodePayload):
    lang = payload.language.lower()

    if lang not in ("python", "java"):
        raise HTTPException(status_code=400, detail="Unsupported language. Use 'python' or 'java'.")
    if lang == "python" and not PYTHON_PATH:
        raise HTTPException(status_code=500, detail="Python interpreter not found on server.")
    if lang == "java" and (not JAVA_PATH or not JAVAC_PATH):
        raise HTTPException(status_code=500, detail="Java not found on server. Please install JDK.")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            if lang == "python":
                file_path = os.path.join(tmpdir, "script.py")
                with open(file_path, "w") as f:
                    f.write(payload.code)
                result = subprocess.run(
                    [PYTHON_PATH, file_path], capture_output=True, text=True, timeout=5, cwd=tmpdir
                )
                return {"stdout": result.stdout, "stderr": result.stderr}

            elif lang == "java":
                file_path = os.path.join(tmpdir, "Main.java")
                with open(file_path, "w") as f:
                    f.write(payload.code)
                compile_result = subprocess.run(
                    [JAVAC_PATH, file_path], capture_output=True, text=True, timeout=10, cwd=tmpdir
                )
                if compile_result.returncode != 0:
                    return {"compile_error": compile_result.stderr, "stdout": "", "stderr": ""}
                run_result = subprocess.run(
                    [JAVA_PATH, "-cp", tmpdir, "Main"], capture_output=True, text=True, timeout=5, cwd=tmpdir
                )
                return {"stdout": run_result.stdout, "stderr": run_result.stderr}

    except subprocess.TimeoutExpired:
        return {"error": "Execution timed out (5s limit)", "stdout": "", "stderr": ""}
    except Exception as e:
        return {"error": str(e), "stdout": "", "stderr": ""}