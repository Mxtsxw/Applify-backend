import shutil, os
from datetime import datetime
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlmodel import Session, select
from app.dependencies import validate_token, get_session
from app.models.sql_models import Resume
from app.models.dto import ResumeRead
from app.config import settings

router = APIRouter()

@router.post("/upload", response_model=Resume)
def upload_resume(
    file: UploadFile = File(...),
    title: str = Form(...),
    token: dict = Depends(validate_token),
    db: Session = Depends(get_session)
):
    user_id = int(token.get("sub"))
    timestamp = int(datetime.utcnow().timestamp())
    safe_filename = f"user_{user_id}_{timestamp}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    resume = Resume(
        user_id=user_id,
        title=title,
        filename=safe_filename,
        file_url=f"/static/resumes/{safe_filename}",
        file_type=file.content_type,
        file_size=os.path.getsize(file_path)
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume

@router.get("/", response_model=List[Resume])
def list_resumes(token: dict = Depends(validate_token), db: Session = Depends(get_session)):
    user_id = int(token.get("sub"))
    return db.exec(select(Resume).where(Resume.user_id == user_id)).all()

@router.delete("/{resume_id}")
def delete_resume(
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