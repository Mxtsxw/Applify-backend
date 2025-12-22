from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session
from app.dependencies import validate_token, get_session
from app.models.schemas import AnalysisRequest, JobPostingAnalysis
from app.services import candidate_service, llm_service

router = APIRouter()

@router.post("/match", response_model=JobPostingAnalysis)
async def analyze_match(
    request: AnalysisRequest, 
    token: dict = Depends(validate_token),
    db: Session = Depends(get_session)
):
    user_id = int(token.get("sub"))
    candidate_text = candidate_service.resolve_candidate_text(db, user_id, request.candidate_context)
    
    if not candidate_text.strip():
        raise HTTPException(status_code=400, detail="No candidate information provided.")

    return await run_in_threadpool(
        llm_service.run_analysis, 
        request.job_posting_content, 
        candidate_text
    )