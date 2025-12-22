from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session, select
from typing import List
from datetime import datetime
import os
import shutil
from app.config import settings
from fastapi import UploadFile, File, Form

from app.dependencies import validate_token, get_session
from app.models.schemas import CoverLetterRequest, ManualCoverLetterRequest
from app.models.sql_models import CoverLetter
from app.services import llm_service
from app.services import candidate_service

router = APIRouter()

@router.post("/generate", response_class=PlainTextResponse)
async def generate_cover_letter(
    request: CoverLetterRequest, 
    token: dict = Depends(validate_token),
    db: Session = Depends(get_session)
):
    # 1. Resolve the candidate text (Resume/Profile)
    user_id = int(token.get("sub"))
    candidate_text = candidate_service.resolve_candidate_text(db, user_id, request.candidate_context)

    # 2. Call Service
    return await run_in_threadpool(
        llm_service.generate_cover_letter,
        request.job_description,
        candidate_text,
        request.analysis_data,
        request.template_content,
        request.language
    )

@router.get("/", response_model=List[CoverLetter])
def list_cover_letters(token: dict = Depends(validate_token), db: Session = Depends(get_session)):
    user_id = int(token.get("sub"))
    return db.exec(select(CoverLetter).where(CoverLetter.user_id == user_id)).all()

@router.post("/manual", response_model=CoverLetter)
def save_manual_cover_letter(
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

@router.post("/ai", response_model=CoverLetter) 
def save_ai_cover_letter(
    data: ManualCoverLetterRequest,
    token: dict = Depends(validate_token),
    db: Session = Depends(get_session)
):
    """Saves an AI-generated cover letter."""
    user_id = int(token.get("sub"))
    cl = CoverLetter(
        user_id=user_id,
        title=data.title,
        content=data.content,
        method="ai-generated"
    )
    db.add(cl)
    db.commit()
    db.refresh(cl)
    return cl

@router.post("/upload", response_model=CoverLetter)
def upload_cover_letter(
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
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
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

@router.delete("/{cl_id}")
def delete_cover_letter(
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
        file_path = os.path.join(settings.UPLOAD_DIR, cl.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            
    db.delete(cl)
    db.commit()
    return {"status": "deleted"}