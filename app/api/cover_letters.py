from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session, select
from typing import List

from app.dependencies import validate_token, get_session
from app.models.schemas import CoverLetterRequest, ManualCoverLetterRequest
from app.models.sql_models import CoverLetter
from app.services import llm_service

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

# ... Add create/save endpoints similar to original code ...