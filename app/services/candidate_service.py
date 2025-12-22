import os
from sqlmodel import Session
from fastapi import HTTPException
from app.models.sql_models import User, Resume
from app.models.schemas import CandidateContext
from app.services import file_service
from app.config import settings

def get_profile_text(user: User) -> str:
    """Formats User Profile from DB."""
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
    parts = []

    # 1. Base Source
    if context.source_type == 'manual':
        parts.append(f"--- MANUAL CANDIDATE INPUT ---\n{context.manual_content or ''}")

    elif context.source_type == 'profile':
        user = db.get(User, user_id)
        if user:
            parts.append(f"--- CANDIDATE PROFILE ---\n{get_profile_text(user)}")

    elif context.source_type == 'resume':
        resume = db.get(Resume, context.source_id)
        if not resume or resume.user_id != user_id:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        file_path = os.path.join(settings.UPLOAD_DIR, resume.filename)
        resume_text = file_service.extract_text_from_file(file_path)
        parts.append(f"--- RESUME CONTENT ({resume.title}) ---\n{resume_text}")

    # 2. Layering
    if context.include_profile_data and context.source_type != 'profile':
        user = db.get(User, user_id)
        if user:
            parts.append(f"--- ADDITIONAL PROFILE CONTEXT ---\n{get_profile_text(user)}")

    return "\n\n".join(parts)