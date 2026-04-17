"""
Data Models (Pydantic Schemas)
==============================
Strict typed models for every stage of the pipeline.
These serve as both validation and documentation of data contracts.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Stage 1: Parsed Resume Structure
# ---------------------------------------------------------------------------
class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    location: Optional[str] = None


class WorkExperience(BaseModel):
    company: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)


class ProjectExperience(BaseModel):
    name: str
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    bullets: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class Education(BaseModel):
    institution: str
    degree: str
    field: Optional[str] = None
    graduation_year: Optional[str] = None
    gpa: Optional[str] = None
    honors: Optional[str] = None


class ParsedResume(BaseModel):
    """Structured output from the Resume Parser module."""
    name: str = ""
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    work_experience: List[WorkExperience] = Field(default_factory=list)
    projects: List[ProjectExperience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 2: Job Description Analysis
# ---------------------------------------------------------------------------
class ParsedJobDescription(BaseModel):
    """Structured output from the JD Analyzer module."""
    job_title: str = ""
    company_name: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    tools_and_technologies: List[str] = Field(default_factory=list)
    key_responsibilities: List[str] = Field(default_factory=list)
    qualifications: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 3: ATS Gap Analysis
# ---------------------------------------------------------------------------
class ATSAnalysis(BaseModel):
    """Output from the ATS Scoring Engine."""
    ats_score: int = Field(ge=0, le=100, description="ATS compatibility score 0-100")
    score_breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Score per category: skills, keywords, experience, etc.",
    )
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 4 & 5: Optimized Resume + Cover Letter
# ---------------------------------------------------------------------------
class OptimizedResume(BaseModel):
    """The fully ATS-optimized resume content ready for DOCX generation."""
    name: str
    contact: ContactInfo
    summary: str
    skills: List[str]
    work_experience: List[WorkExperience]
    projects: List[ProjectExperience]
    education: List[Education]
    achievements: List[str]
    certifications: List[str] = Field(default_factory=list)


class CoverLetter(BaseModel):
    """Generated cover letter content."""
    recipient_name: Optional[str] = None
    company_name: str
    job_title: str
    opening_paragraph: str
    body_paragraph_1: str
    body_paragraph_2: str
    closing_paragraph: str
    full_text: str  # Assembled full letter


# ---------------------------------------------------------------------------
# API Request / Response Models
# ---------------------------------------------------------------------------
class PipelineRequest(BaseModel):
    """Input to trigger the full pipeline (used internally after file upload)."""
    job_description: str = Field(..., min_length=50, description="Raw job description text")
    resume_text: str = Field(..., min_length=100, description="Extracted resume text")


class PipelineResponse(BaseModel):
    """Full pipeline response returned to the frontend."""
    parsed_resume: ParsedResume
    parsed_jd: ParsedJobDescription
    ats_analysis: ATSAnalysis
    optimized_resume: OptimizedResume
    cover_letter: CoverLetter
    resume_docx_path: Optional[str] = None
    cover_letter_docx_path: Optional[str] = None
    processing_time_seconds: Optional[float] = None


class ErrorResponse(BaseModel):
    detail: str
    stage: Optional[str] = None  # Which pipeline stage failed
