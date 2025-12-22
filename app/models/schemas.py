from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class UserProfileUpdate(BaseModel):
    """
    Defines the allowed fields for updating a user profile.
    """
    full_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    skills: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None

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

class CandidateContext(BaseModel):
    source_type: Literal['resume', 'profile', 'manual']
    source_id: Optional[int] = None
    manual_content: Optional[str] = None
    include_profile_data: bool = False
    
class AnalysisRequest(BaseModel):
    job_posting_content: str = Field(..., description="Content of the job posting to analyze.")
    candidate_context: CandidateContext = Field(..., description="Context about the candidate's source and profile data inclusion.")

class CoverLetterRequest(BaseModel):
    job_description: str = Field(..., description="Full text of the job posting.")
    candidate_context: CandidateContext = Field(..., description="Context about the candidate's source and profile data inclusion.")
    analysis_data: JobPostingAnalysis = Field(..., description="Structured analysis results used for personalization.")
    template_content: Optional[str] = Field(None, description="User's custom template from the frontend (can be null).")
    language: str = Field(default="English", description="Target language (e.g., 'French', 'English').")

class ManualCoverLetterRequest(BaseModel):
    title: str
    content: str

