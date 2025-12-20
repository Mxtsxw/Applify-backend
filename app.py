import logging
import os
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.concurrency import run_in_threadpool
from models import AnalysisRequest, JobPostingAnalysis, CoverLetterRequest
from llm import run_llm_analysis_chain, generate_cover_letter_chain
from datetime import datetime
from fastapi.responses import RedirectResponse
from authlib.jose import jwt, JsonWebKey

from fastapi import FastAPI, HTTPException, Request, Depends
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from sqlmodel import Session, select

from dotenv import load_dotenv
load_dotenv()

# Import our new DB tools
from database import create_db_and_tables, get_session, User

# --- Lifecycle: Connect to DB on Start ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    logging.info("Database tables verified.")
    yield

# Initialize FastAPI App
app = FastAPI(
    title="Applify",
    description="AI-powered job/profile alignment assessment."
)

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
            # --- CREATE NEW USER ---
            logging.info(f"New user detected: {email}")
            user = User(
                email=email,
                name=user_info.get("name"),
                picture_url=user_info.get("picture"),
                provider="google", # Mark as Google for now
            )
            db.add(user)
        else:
            # --- UPDATE EXISTING USER ---
            logging.info(f"Welcome back: {email}")
            user.last_login = datetime.utcnow()
            # Optional: Update picture or name if they changed on Google
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
            "exp": 3600
        }
        
        # authlib.jose.jwt.encode returns bytes, so we decode to string
        frontend_token = jwt.encode(
            {'alg': 'HS256'}, 
            payload, 
            SECRET_KEY
        ).decode('utf-8')

        # Redirect to Frontend
        FRONTEND_URL = os.getenv("FRONTEND_AUTH_CALLBACK_URL") 
        
        # We pass the token in the URL query parameter
        return RedirectResponse(url=f"{FRONTEND_URL}?token={frontend_token}")

    except Exception as e:
        logging.error(f"Auth Error: {e}")
        raise RedirectResponse(url=f"{FRONTEND_URL}?error=Authentication%20Failed")

@app.get("/api/v1/users/me")
async def get_current_user(request: Request, db: Session = Depends(get_session)):
    """
    Test endpoint to verify the session works.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.get(User, user_id)
    return user

@app.post("/api/v1/analyze-match/", response_model=JobPostingAnalysis)
async def analyze_job_posting(request: AnalysisRequest):
    """
    Takes a job posting URL and returns a structured analysis object
    by running a LangChain pipeline.
    
    Note: The use of run_in_threadpool is VITAL here. It runs the
    blocking, synchronous LLM code in a separate thread, keeping
    FastAPI's main event loop free for high concurrency.
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
async def generate_cover_letter(request_data: CoverLetterRequest):
    """
    Receives all necessary inputs (Job, Profile, Analysis, Template) and calls the 
    LLM chain to generate a final, personalized cover letter text.
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
            request_data.template_content
        )
        
        return final_letter_text

    except Exception as e:
        logging.error(f"Error during LLM cover letter generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate letter due to a service error. Details: {e}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)