import os
import logging
import requests
from fastapi import HTTPException
from PyPDF2 import PdfReader
from docx import Document
from database import User, Resume
from models import CandidateContext
from sqlmodel import Session

TEMPLATE_FILE_PATH = os.path.join(os.path.dirname(__file__), "templates", "coverLetter.txt")
_DEFAULT_TEMPLATE_CACHE: str | None = None

def get_default_template() -> str:
    """
    Reads and returns the default cover letter template from the file system.
    Caches the result after the first read.
    """
    global _DEFAULT_TEMPLATE_CACHE
    
    if _DEFAULT_TEMPLATE_CACHE is not None:
        return _DEFAULT_TEMPLATE_CACHE

    if not os.path.exists(TEMPLATE_FILE_PATH):
        logging.error(f"Template file not found at path: {TEMPLATE_FILE_PATH}")
        # Return a simple fallback if the file is missing to prevent crash
        return "Error: Template file missing. Please configure templates/coverLetter.txt."

    try:
        with open(TEMPLATE_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            _DEFAULT_TEMPLATE_CACHE = content
            return content
    except Exception as e:
        logging.error(f"Error reading template file {TEMPLATE_FILE_PATH}: {e}")
        return "Error: Could not read template content."

def fetch_content_from_url(url: str) -> str:
    """
    Simulates loading the main text content from a URL.
    In a real app, this would involve a library like BeautifulSoup
    or LangChain's WebBaseLoader to parse and clean the HTML.
    """
    try:
        # Use a timeout to prevent hanging the worker thread
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
        
        # --- Placeholder for HTML/Job Description Extraction ---
        # In a real application, you would parse 'response.text' here
        # to isolate the actual job description text.
        
        mock_job_description = (
            "Job Title: Senior Data Scientist. Location: Remote. "
            "We are looking for an experienced Data Scientist to join our team. "
            "Requires 5+ years of experience with Python, Pandas, and Scikit-learn. "
            "Must have strong communication skills and experience deploying models with AWS. "
            "Experience with Kubernetes is a huge plus. Agile experience required."
        )
        return mock_job_description
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch content from URL: {e}")

def extract_text_from_file(file_path: str) -> str:
    """Robustly extracts text from PDF, DOCX, or TXT files."""
    if not os.path.exists(file_path):
        return "[Error: File not found on server]"
    
    ext = file_path.split('.')[-1].lower()
    text = ""

    try:
        if ext == 'pdf':
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif ext in ['docx', 'doc']:
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            return "[Error: Unsupported file format.]"
            
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return "[Error: Could not parse file content.]"

    return text.strip()

def get_profile_text(db: Session, user_id: int) -> str:
    """
    Strictly fetches and formats the User Profile from the DB.
    Does NOT handle logic for resumes or manual text.
    """
    user = db.get(User, user_id)
    if not user:
        return "[Error: User profile not found.]"

    # Clean formatting
    parts = [
        f"Name: {user.name}",
        f"Title: {user.title or 'N/A'}",
        f"Summary: {user.summary or 'N/A'}",
        f"Skills: {user.skills or 'N/A'}",
        f"Experience: {user.experience or 'N/A'}",
        f"Education: {user.education or 'N/A'}"
    ]
    return "\n".join(parts)

def resolve_candidate_text(db: Session, user_id: int, context: CandidateContext) -> str:
    """
    Orchestrator: Builds the final string based on the 5 interaction cases.
    """
    parts = []

    # --- 1. RESOLVE BASE SOURCE ---
    if context.source_type == 'manual':
        content = context.manual_content or ""
        parts.append(f"--- MANUAL CANDIDATE INPUT ---\n{content}")

    elif context.source_type == 'profile':
        # Fetch profile directly using the helper
        profile_content = get_profile_text(db, user_id)
        parts.append(f"--- CANDIDATE PROFILE ---\n{profile_content}")

    elif context.source_type == 'resume':
        resume = db.get(Resume, context.source_id)
        # Security check: Ensure resume belongs to the authenticated user
        if not resume or resume.user_id != user_id:
            raise HTTPException(status_code=404, detail="Resume not found or access denied")
        
        # Construct absolute path (Ensure 'uploads' exists in your root)
        file_path = os.path.abspath(os.path.join("uploads", resume.filename))
        resume_text = extract_text_from_file(file_path)
        
        parts.append(f"--- RESUME CONTENT ({resume.title}) ---\n{resume_text}")

    # --- 2. APPLY LAYERING (Toggle) ---
    # Inject profile data if requested AND if the base source wasn't already the profile
    if context.include_profile_data and context.source_type != 'profile':
        profile_content = get_profile_text(db, user_id)
        parts.append(f"--- ADDITIONAL PROFILE CONTEXT ---\n{profile_content}")

    return "\n\n".join(parts)