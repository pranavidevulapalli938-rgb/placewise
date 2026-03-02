
from fastapi import FastAPI, Depends, HTTPException, Request
from bs4 import BeautifulSoup
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import subprocess
import tempfile
import os
from dotenv import load_dotenv
from database import engine, SessionLocal
from models import Base, User, Application, ApplicationStatusHistory, Note
from schemas import UserCreate, UserResponse, UserLogin, ApplicationCreate, ApplicationResponse, StatusUpdate, NoteCreate, CodePayload
from auth import hash_password, verify_password, create_access_token, decode_access_token
from fastapi.middleware.cors import CORSMiddleware

PYTHON_PATH = r"C:\Program Files\Python313\python.exe"
JAVA_PATH = r"C:\Program Files\Java\jdk-25.0.2\bin\java.exe"
JAVAC_PATH = r"C:\Program Files\Java\jdk-25.0.2\bin\javac.exe"

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Create FastAPI App
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For production, replace with your extension ID
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)

load_dotenv()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")


# Dependency: Get database session
def get_db():
    db = SessionLocal() #Open a database connection and create a session for interacting with the database. This session will be used in the route handlers to perform database operations.
    try:
        yield db
    finally:
        db.close()


# Root route for testing
@app.get("/")
def read_root():
    return {"message": "Backend Running"}


# Register User
@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if the user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password before saving
    hashed_pw = hash_password(user.password)

    # Create and persist the new user
    new_user = User(email=user.email, password=hashed_pw)
    
     # Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user) #get updated data
   
   # Return user (without password because of response_model)
    return new_user


#login user 

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)): #Session comes from SQLAlchemy, It is used to talk to the database
    # Check if the user exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    
    if not existing_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Verify the password
    if not verify_password(user.password, existing_user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Create access token
    access_token = create_access_token(
      data={"user_id": existing_user.id}
    )

    return {
          "access_token": access_token,
          "token_type": "bearer"
      }
    
    

security = HTTPBearer()

@app.post("/applications")
def add_application(
    app_data: ApplicationCreate,
    db: Session = Depends(get_db),
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    # 1. Decode token
    token = auth.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("user_id")

    # 2. 🔍 CHECK FOR DUPLICATE
    existing_app = db.query(Application).filter(
        Application.user_id == user_id,
        Application.company == app_data.company,
        Application.role == app_data.role
    ).first()

    if existing_app:
        existing_app.status = "Applied"
        db.commit()
        db.refresh(existing_app)
        return {
            "message": "already_exists",
            "id": existing_app.id
    }

    # 3. If not exists → create new
    new_app = Application(
        user_id=user_id,
        company=app_data.company,
        role=app_data.role,
        status="Applied"
    )

    db.add(new_app)
    db.commit()
    db.refresh(new_app)

    return {
        "message": "created",
        "id": new_app.id
}

@app.get("/applications")
def get_applications(
    db: Session = Depends(get_db),
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    token = auth.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("user_id")

    apps = db.query(Application).filter(
        Application.user_id == user_id
    ).all()

    return apps

#Purpose : find application by id and update its status. Also add an entry to the application status history table to keep track of status changes over time.

#Update application status and store the change in history
@app.patch("/applications/{app_id}/status")
def update_status(
    app_id : int,
    status_data : StatusUpdate,
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found") #Stop execution
    
    # Update the application status
    app.status = status_data.status


    # Add to status history
    history = ApplicationStatusHistory(
        application_id = app.id,
        status = status_data.status
    )
    
    db.add(history)
    db.commit()
    
    return {"message": "Status updated successfully"}



@app.post("/applications/{app_id}/notes")
def add_note(
    app_id : int,
    note : NoteCreate,
    db: Session = Depends(get_db)
):
    
    application = db.query(Application).filter(Application.id == app_id).first()
    
    if not application:
        raise HTTPException(status_code = 404, detail = "Application not found")
    
    new_note = Note(
        application_id = app_id,
        text = note.text
    )
    
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    
    return {"message": "Note added successfully"}


@app.get("/applications/{app_id}/notes")
def get_notes(
    app_id : int, 
    db : Session = Depends(get_db)
):
    notes = db.query(Note).filter(Note.application_id == app_id).all()
    
    return notes


# ---------- CODE EXECUTION ----------

@app.post("/execute")
def execute_code(payload: CodePayload):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:

            # ---------------- PYTHON ----------------
            if payload.language == "python":
                file_path = os.path.join(tmpdir, "script.py")

                with open(file_path, "w") as f:
                    f.write(payload.code)

                result = subprocess.run(
                    [PYTHON_PATH, file_path],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

            # ---------------- JAVA ----------------
            elif payload.language == "java":
                file_path = os.path.join(tmpdir, "Main.java")

                with open(file_path, "w") as f:
                    f.write(payload.code)

                compile_step = subprocess.run(
                    [JAVAC_PATH, file_path],
                    capture_output=True,
                    text=True
                )

                if compile_step.stderr:
                    return {"compile_error": compile_step.stderr}

                result = subprocess.run(
                    [JAVA_PATH, "-cp", tmpdir, "Main"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

            else:
                return {"error": "Unsupported language"}

            return {
                "stdout": result.stdout,
                "stderr": result.stderr
            }

    except Exception as e:
        return {"error": str(e)}
    
