from typing import List, Optional
from pydantic import BaseModel, Field

class AnalysisBreakdown(BaseModel):
    skillsMatch: int = Field(..., description="Percentage match for technical skills (0-100).")
    experienceMatch: int = Field(..., description="Percentage match for required years/type of experience (0-100).")
    qualificationsMatch: int = Field(..., description="Percentage match for degrees/certifications (0-100).")
    cultureMatch: int = Field(..., description="Percentage match for work style and values (0-100).")


class JobPostingAnalysis(BaseModel):
    """The full, structured response from the LLM, matching the AnalysisResult interface."""
    overallScore: int = Field(..., description="Overall percentage match score (0-100).")

    breakdown: AnalysisBreakdown 
    
    matchedSkills: List[str] = Field(..., description="List of skills successfully matched between resume and job.")
    missingSkills: List[str] = Field(..., description="List of critical skills required by the job but missing in the resume.")

    insights: List[str] = Field(..., description="4-5 concise bullet points summarizing the match results.")

    class Config:
        populate_by_name = True 
        validate_by_name = True


class AnalysisRequest(BaseModel):
    job_posting_content: str = Field(..., description="Content of the job posting to analyze.")
    resume_text: Optional[str] = Field(None, description="The user's resume/profile text (optional for now).")

class CoverLetterRequest(BaseModel):
    job_description: str = Field(..., description="Full text of the job posting.")
    profile_content: str = Field(..., description="Candidate's profile/resume text.")
    analysis_data: JobPostingAnalysis = Field(..., description="Structured analysis results used for personalization.")
    template_content: Optional[str] = Field(None, description="User's custom template from the frontend (can be null).")