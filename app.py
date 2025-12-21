import logging
import os
import time
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.concurrency import run_in_threadpool
from models import AnalysisRequest, JobPostingAnalysis, CoverLetterRequest, UserProfileUpdate, ManualCoverLetterRequest
from llm import run_llm_analysis_chain, generate_cover_letter_chain
from datetime import datetime
from fastapi.responses import RedirectResponse
from authlib.jose import jwt, JsonWebKey, JoseError

from fastapi import FastAPI, HTTPException, Request, Depends, Security, status
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from sqlmodel import Session, select
from typing import List

import shutil
from fastapi import UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from database import create_db_and_tables, get_session, User, Resume, CoverLetter
from pydantic import BaseModel

# --- Lifecycle: Connect to DB on Start ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    logging.info("Database tables verified.")
    yield

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize FastAPI App
app = FastAPI(
    title="Applify",
    description="AI-powered job/profile alignment assessment."
)
app.mount("/static/resumes", StaticFiles(directory="uploads"), name="resumes")

# Load secret from env or default for dev
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-dev-secret")

# SessionMiddleware is required for OAuth to store "state" cookies
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Set up CORS middleware
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth Utilities ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/google")

def validate_token(token: str = Depends(oauth2_scheme)):
    """
    Decodes and validates the JWT token from the Authorization header.
    Returns the user payload (ID, email, etc.) if valid.
    """
    logging.info("Validating token for current user.")
    try:
        # 1. Decode the token using the SAME secret key used to sign it
        payload = jwt.decode(token, SECRET_KEY)
        
        # 2. Validate claims (checks if token is expired 'exp')
        payload.validate()
        
        logging.info(f"Token valid for user ID: {payload.get('sub')}, email: {payload.get('email')}")
        return payload

    except JoseError as e:
        logging.error(f"Token validation error: {e}")
        # If signature is wrong or token is expired
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Configure Google OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_AUTH_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_AUTH_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy"}

@app.get("/api/v1/auth/google", tags=["Auth"])
async def login(request: Request):
    """
    Redirects the user to the Google Login page.
    """
    redirect_uri = "http://localhost:8000/api/v1/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/api/v1/auth/google/callback")
async def auth_callback_google(request: Request, db: Session = Depends(get_session)):
    """
    Handles the callback from Google.
    Logic: Find User by Email ? Log them in : Create new User.
    """
    # Redirect to Frontend
    FRONTEND_URL = os.getenv("FRONTEND_AUTH_CALLBACK_URL") 

    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        email = user_info.get("email")
        
        # 1. Check if user exists (The "Golden Key" Lookup)
        statement = select(User).where(User.email == email)
        user = db.exec(statement).first()
        
        if not user:
            logging.info(f"New user detected: {email}")
            user = User(
                email=email,
                name=user_info.get("name"),
                picture_url=user_info.get("picture"),
                provider="google",
            )
            db.add(user)
        else:
            logging.info(f"Welcome back: {email}")
            user.last_login = datetime.utcnow()
            user.name = user_info.get("name") 
            user.picture_url = user_info.get("picture")
            db.add(user)
            
        db.commit()
        db.refresh(user)

        # 1. Generate a Token for the Frontend
        # We put the user info inside so AuthContext can read it immediately
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
            "picture": user.picture_url,
            "exp": int(time.time()) + 3600  # 1 hour expiration
        }
        
        # authlib.jose.jwt.encode returns bytes, so we decode to string
        frontend_token = jwt.encode(
            {'alg': 'HS256'}, 
            payload, 
            SECRET_KEY
        ).decode('utf-8')
        
        # We pass the token in the URL query parameter
        return RedirectResponse(url=f"{FRONTEND_URL}?token={frontend_token}")

    except Exception as e:
        logging.error(f"Auth Error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}?error=Authentication%20Failed")

@app.get("/api/v1/users/me")
async def get_current_user(
    token_payload: dict = Depends(validate_token),
    db: Session = Depends(get_session)
):
    """
    Fetches the current user using the JWT token (Stateless).
    """
    user_id = token_payload.get('sub')
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@app.post("/api/v1/analyze-match/", response_model=JobPostingAnalysis)
async def analyze_job_posting(request: AnalysisRequest, token: str = Depends(validate_token)):
    """
    Takes a job posting URL and returns a structured analysis object
    by running a LangChain pipeline.
    
    Note: The use of run_in_threadpool is VITAL here. It runs the
    blocking, synchronous LLM code in a separate thread, keeping
    FastAPI's main event loop free for high concurrency.
    
    Requires: Bearer token authentication
    """
    job_description = request.job_posting_content
    profile_description = request.resume_text or ""

    # 2. Run the heavy LLM analysis
    analysis_result = await run_in_threadpool(run_llm_analysis_chain, job_description, profile_description)

    # 3. Return the result
    return analysis_result

@app.post("/api/v1/generate-cover-letter", 
             response_class=PlainTextResponse,
             status_code=200,
             summary="Generate personalized cover letter using LLM.")
async def generate_cover_letter(request_data: CoverLetterRequest, token: str = Depends(validate_token)):
    """
    Receives all necessary inputs (Job, Profile, Analysis, Template) and calls the 
    LLM chain to generate a final, personalized cover letter text.
    
    Requires: Bearer token authentication
    """
    logging.info("Received request for cover letter generation via app.post.")
    
    if not request_data.job_description or not request_data.profile_content:
        raise HTTPException(
            status_code=400,
            detail="Job description and profile content are required for generation."
        )

    try:
        final_letter_text = await run_in_threadpool(
            generate_cover_letter_chain,
            request_data.job_description,
            request_data.profile_content,
            request_data.analysis_data,
            request_data.template_content,
            request_data.language
        )
        
        return final_letter_text

    except Exception as e:
        logging.error(f"Error during LLM cover letter generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate letter due to a service error. Details: {e}"
        )

# -- User Profile Update Endpoint ---
@app.get("/api/v1/profile/me", response_model=User)
async def get_my_profile(
    token: dict = Depends(validate_token), 
    db: Session = Depends(get_session)
):
    """
    Fetches the full profile of the currently logged-in user.
    """
    user_id = token.get("sub")
    user = db.get(User, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return user

@app.put("/api/v1/profile/me", response_model=User)
async def update_my_profile(
    profile_data: UserProfileUpdate, 
    token: dict = Depends(validate_token), 
    db: Session = Depends(get_session)
):
    """
    Updates the logged-in user's profile information.
    """

    logging.info(f"Updating profile for user ID: {token.get('sub')}")
    user_id = token.get("sub")
    user = db.get(User, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if profile_data.full_name:
        user.name = profile_data.full_name
        
    update_data = profile_data.model_dump(exclude_unset=True, exclude={"full_name"})
    
    for key, value in update_data.items():
        setattr(user, key, value)

    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

# --- RESUME ENDPOINTS ---

@app.post("/api/v1/resumes/upload", response_model=Resume)
async def upload_resume(
    file: UploadFile = File(...),
    title: str = Form(...),
    token: dict = Depends(validate_token),
    db: Session = Depends(get_session)
):
    """Uploads a resume file and links it to the user."""
    user_id = int(token.get("sub"))
    
    # 1. Generate unique filename to prevent collisions
    # e.g. "user_123_timestamp_filename.pdf"
    timestamp = int(datetime.utcnow().timestamp())
    safe_filename = f"user_{user_id}_{timestamp}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    
    # 2. Save file to disk
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 3. Create DB Entry
    file_url = f"/static/resumes/{safe_filename}"
    file_size = os.path.getsize(file_path)
    
    resume = Resume(
        user_id=user_id,
        title=title,
        filename=safe_filename,
        file_url=file_url,
        file_type=file.content_type or "application/pdf",
        file_size=file_size,
        status="active"
    )
    
    db.add(resume)
    db.commit()
    db.refresh(resume)
    
    return resume

@app.get("/api/v1/resumes", response_model=List[Resume])
async def list_resumes(
    token: dict = Depends(validate_token),
    db: Session = Depends(get_session)
):

    logging.info("Listing resumes for current user.")
    """Lists all resumes for the current user."""
    user_id = int(token.get("sub"))
    statement = select(Resume).where(Resume.user_id == user_id).order_by(Resume.upload_date.desc())
    resumes = db.exec(statement).all()
    logging.info(f"User ID {user_id} has {len(resumes)} resumes.")
    return resumes

@app.delete("/api/v1/resumes/{resume_id}")
async def delete_resume(
    resume_id: int,
    token: dict = Depends(validate_token),
    db: Session = Depends(get_session)
):
    """Deletes a resume from DB and Disk."""
    user_id = int(token.get("sub"))
    resume = db.get(Resume, resume_id)
    
    if not resume or resume.user_id != user_id:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    # 1. Remove from Disk
    file_path = UPLOAD_DIR / resume.filename
    if file_path.exists():
        os.remove(file_path)
        
    # 2. Remove from DB
    db.delete(resume)
    db.commit()
    
    return {"status": "deleted", "id": resume_id}

# --- COVER LETTER ENDPOINTS ---

@app.get("/api/v1/cover-letters", response_model=List[CoverLetter])
async def list_cover_letters(
    token: dict = Depends(validate_token),
    db: Session = Depends(get_session)
):
    """Lists all cover letters for the current user."""
    user_id = int(token.get("sub"))
    statement = select(CoverLetter).where(CoverLetter.user_id == user_id).order_by(CoverLetter.created_at.desc())
    return db.exec(statement).all()

@app.post("/api/v1/cover-letters/manual", response_model=CoverLetter)
async def create_manual_cover_letter(
    data: ManualCoverLetterRequest,
    token: dict = Depends(validate_token),
    db: Session = Depends(get_session)
):
    """Saves a manually written cover letter."""
    user_id = int(token.get("sub"))
    
    cl = CoverLetter(
        user_id=user_id,
        title=data.title,
        content=data.content,
        method="manual"
    )
    db.add(cl)
    db.commit()
    db.refresh(cl)
    return cl

@app.post("/api/v1/cover-letters/upload", response_model=CoverLetter)
async def upload_cover_letter(
    file: UploadFile = File(...),
    title: str = Form(...),
    token: dict = Depends(validate_token),
    db: Session = Depends(get_session)
):
    """Uploads a cover letter file (PDF/Doc)."""
    user_id = int(token.get("sub"))
    
    # Save file
    timestamp = int(datetime.utcnow().timestamp())
    safe_filename = f"cl_{user_id}_{timestamp}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    cl = CoverLetter(
        user_id=user_id,
        title=title,
        filename=safe_filename,
        file_url=f"/static/resumes/{safe_filename}", 
        file_type=file.content_type,
        method="upload"
    )
    db.add(cl)
    db.commit()
    db.refresh(cl)
    return cl

@app.delete("/api/v1/cover-letters/{cl_id}")
async def delete_cover_letter(
    cl_id: int,
    token: dict = Depends(validate_token),
    db: Session = Depends(get_session)
):
    user_id = int(token.get("sub"))
    cl = db.get(CoverLetter, cl_id)
    
    if not cl or cl.user_id != user_id:
        raise HTTPException(status_code=404, detail="Cover letter not found")
        
    # Delete file if exists
    if cl.method == "upload" and cl.filename:
        file_path = UPLOAD_DIR / cl.filename
        if file_path.exists():
            os.remove(file_path)
            
    db.delete(cl)
    db.commit()
    return {"status": "deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)