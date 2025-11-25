from typing import List, Optional
from pydantic import BaseModel, Field

# Output Schema: The full, structured response from the LLM
class JobPostingAnalysis(BaseModel):
    overall_match_score: int = Field(..., description="Overall percentage match score (0-100).")
    skills_match: int = Field(..., description="Percentage match for technical skills (0-100).")
    experience_match: int = Field(..., description="Percentage match for required years/type of experience (0-100).")
    qualifications_match: int = Field(..., description="Percentage match for degrees/certifications (0-100).")
    culture_match: int = Field(..., description="Percentage match for work style and values (0-100).")

    matched_skills: List[str] = Field(..., description="List of skills successfully matched between resume and job.")
    skills_to_develop: List[str] = Field(..., description="List of critical skills required by the job but missing in the resume.")

    key_insights: List[str] = Field(..., description="4-5 concise bullet points summarizing the match results.")

# Input Schema: What the React frontend sends
class AnalysisRequest(BaseModel):
    job_posting_content: str = Field(..., description="Content of the job posting to analyze.")
    resume_text: Optional[str] = Field(None, description="The user's resume/profile text (optional for now).")