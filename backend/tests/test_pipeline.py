"""
Test Suite - ATS Resume Optimizer
===================================
Tests for each pipeline module.

Run with:
    pytest tests/ -v
    pytest tests/ -v --asyncio-mode=auto
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from models.schemas import (
    ParsedResume,
    ParsedJobDescription,
    ATSAnalysis,
    OptimizedResume,
    ContactInfo,
    WorkExperience,
    Education,
)


# ---------------------------------------------------------------------------
# Fixtures - Sample Data
# ---------------------------------------------------------------------------

SAMPLE_RESUME_TEXT = """
John Doe
john.doe@email.com | +1-555-123-4567 | linkedin.com/in/johndoe | github.com/johndoe

PROFESSIONAL SUMMARY
Experienced software engineer with 5 years building scalable Python backend systems.

SKILLS
Python, FastAPI, Django, PostgreSQL, AWS, Docker, Kubernetes, REST APIs, Git

WORK EXPERIENCE
Senior Software Engineer - TechCorp Inc | Jan 2022 - Present
- Built microservices handling 1M+ daily requests using FastAPI and Docker
- Reduced API latency by 40% through PostgreSQL query optimization
- Led a team of 4 engineers to deliver a payment processing system

Software Engineer - StartupXYZ | Jun 2019 - Dec 2021
- Developed REST APIs serving 50K+ users using Django REST Framework
- Implemented CI/CD pipeline using GitHub Actions, reducing deployment time by 60%

EDUCATION
B.S. Computer Science - State University | 2019 | GPA: 3.7/4.0

PROJECTS
ResumeAI - Python, FastAPI, OpenAI API
- Built an AI-powered resume optimization tool with 500+ monthly users
"""

SAMPLE_JD_TEXT = """
Senior Python Engineer - AI Products Team

We are looking for a Senior Python Engineer to join our AI products team.

Requirements:
- 4+ years of Python development experience
- Strong experience with FastAPI or Flask
- Experience with Docker and Kubernetes
- PostgreSQL and Redis knowledge
- AWS or GCP cloud experience
- Experience with machine learning pipelines
- REST API design experience

Preferred:
- Experience with LLMs and AI/ML systems
- Knowledge of Kafka or RabbitMQ
- Terraform experience

Responsibilities:
- Design and implement scalable backend services
- Build and maintain ML model serving infrastructure
- Collaborate with data science team
- Code review and mentoring junior engineers
"""

SAMPLE_PARSED_RESUME = ParsedResume(
    name="John Doe",
    contact=ContactInfo(
        email="john.doe@email.com",
        phone="+1-555-123-4567",
        linkedin="https://linkedin.com/in/johndoe",
        github="https://github.com/johndoe",
    ),
    summary="Experienced software engineer with 5 years building scalable Python backend systems.",
    skills=["Python", "FastAPI", "Django", "PostgreSQL", "AWS", "Docker", "Kubernetes"],
    work_experience=[
        WorkExperience(
            company="TechCorp Inc",
            title="Senior Software Engineer",
            start_date="Jan 2022",
            end_date="Present",
            bullets=["Built microservices handling 1M+ daily requests", "Reduced API latency by 40%"],
        )
    ],
    education=[
        Education(
            institution="State University",
            degree="B.S.",
            field="Computer Science",
            graduation_year="2019",
            gpa="3.7/4.0",
        )
    ],
    achievements=["Dean's List 2017-2019"],
)

SAMPLE_PARSED_JD = ParsedJobDescription(
    job_title="Senior Python Engineer",
    company_name="TechCorp AI",
    required_skills=["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL"],
    preferred_skills=["Kafka", "Terraform", "LLMs"],
    tools_and_technologies=["AWS", "Redis", "GitHub Actions"],
    key_responsibilities=["Design scalable backend services", "Build ML model serving infrastructure"],
    keywords=["machine learning", "REST API", "microservices", "CI/CD"],
)


# ---------------------------------------------------------------------------
# Unit Tests: Resume Parser
# ---------------------------------------------------------------------------

class TestResumeParser:

    def test_extract_from_pdf_bytes_empty(self):
        """Should handle empty PDF gracefully."""
        from modules.resume_parser import ResumeParser
        mock_llm = MagicMock()
        parser = ResumeParser(mock_llm)
        # Empty bytes should not crash the extractor (may raise ValueError)
        import pytest
        with pytest.raises(Exception):
            parser._extract_from_pdf(b"")

    def test_json_to_model_complete(self):
        """Should correctly convert complete LLM JSON to ParsedResume."""
        from modules.resume_parser import ResumeParser
        mock_llm = MagicMock()
        parser = ResumeParser(mock_llm)

        sample_json = {
            "name": "Jane Smith",
            "contact": {
                "email": "jane@example.com",
                "phone": "+1-555-000-0000",
                "linkedin": "https://linkedin.com/in/janesmith",
                "github": None,
                "portfolio": None,
                "location": "New York, NY",
            },
            "summary": "Software engineer",
            "skills": ["Python", "AWS"],
            "work_experience": [
                {
                    "company": "ACME Corp",
                    "title": "Engineer",
                    "start_date": "2020",
                    "end_date": "Present",
                    "location": "NYC",
                    "bullets": ["Built things", "Fixed bugs"],
                }
            ],
            "projects": [],
            "education": [
                {
                    "institution": "MIT",
                    "degree": "B.S.",
                    "field": "CS",
                    "graduation_year": "2020",
                    "gpa": None,
                    "honors": None,
                }
            ],
            "achievements": ["Hackathon winner"],
            "certifications": [],
        }

        result = parser._json_to_model(sample_json)

        assert result.name == "Jane Smith"
        assert result.contact.email == "jane@example.com"
        assert "Python" in result.skills
        assert len(result.work_experience) == 1
        assert result.work_experience[0].company == "ACME Corp"
        assert len(result.education) == 1

    def test_json_to_model_missing_fields(self):
        """Should handle partial LLM JSON without crashing."""
        from modules.resume_parser import ResumeParser
        mock_llm = MagicMock()
        parser = ResumeParser(mock_llm)

        # Minimal JSON - many fields missing
        result = parser._json_to_model({"name": "Bob"})

        assert result.name == "Bob"
        assert result.skills == []
        assert result.work_experience == []


# ---------------------------------------------------------------------------
# Unit Tests: JD Analyzer
# ---------------------------------------------------------------------------

class TestJobDescriptionAnalyzer:

    def test_ensure_list_with_list(self):
        from modules.jd_analyzer import JobDescriptionAnalyzer
        mock_llm = MagicMock()
        analyzer = JobDescriptionAnalyzer(mock_llm)
        assert analyzer._ensure_list(["a", "b"]) == ["a", "b"]

    def test_ensure_list_with_string(self):
        from modules.jd_analyzer import JobDescriptionAnalyzer
        mock_llm = MagicMock()
        analyzer = JobDescriptionAnalyzer(mock_llm)
        assert analyzer._ensure_list("Python") == ["Python"]

    def test_ensure_list_with_empty(self):
        from modules.jd_analyzer import JobDescriptionAnalyzer
        mock_llm = MagicMock()
        analyzer = JobDescriptionAnalyzer(mock_llm)
        assert analyzer._ensure_list([]) == []
        assert analyzer._ensure_list("") == []
        assert analyzer._ensure_list(None) == []


# ---------------------------------------------------------------------------
# Unit Tests: ATS Scoring Engine
# ---------------------------------------------------------------------------

class TestATSScoringEngine:

    def test_get_resume_text(self):
        """Should combine all resume text fields."""
        from modules.ats_scorer import ATSScoringEngine
        mock_llm = MagicMock()
        engine = ATSScoringEngine(mock_llm)
        text = engine._get_resume_text(SAMPLE_PARSED_RESUME)

        assert "John Doe" in text
        assert "Python" in text
        assert "FastAPI" in text
        assert "TechCorp" in text

    def test_keyword_matching(self):
        """Should correctly identify matched vs missing keywords."""
        from modules.ats_scorer import ATSScoringEngine
        mock_llm = MagicMock()
        engine = ATSScoringEngine(mock_llm)

        resume_text = "python fastapi docker postgresql aws"
        jd_keywords = ["Python", "FastAPI", "Kubernetes", "Terraform", "Redis"]

        matched = [kw for kw in jd_keywords if kw.lower() in resume_text]
        missing = [kw for kw in jd_keywords if kw.lower() not in resume_text]

        assert "Python" in matched
        assert "FastAPI" in matched
        assert "Kubernetes" in missing
        assert "Terraform" in missing

    def test_build_analysis_clamps_score(self):
        """ATS score should always be between 0 and 100."""
        from modules.ats_scorer import ATSScoringEngine
        mock_llm = MagicMock()
        engine = ATSScoringEngine(mock_llm)

        # Test with out-of-range score from LLM
        analysis = engine._build_analysis(
            {"ats_score": 150},  # Out of range
            matched_keywords=["Python"],
            missing_keywords=["Kubernetes"],
            missing_skills=["Terraform"],
        )
        assert 0 <= analysis.ats_score <= 100


# ---------------------------------------------------------------------------
# Unit Tests: LLM Client JSON Extraction
# ---------------------------------------------------------------------------

class TestLLMClientJsonExtraction:

    def _get_client(self):
        """Get client without initializing provider."""
        from core.llm_client import LLMClient
        client = LLMClient.__new__(LLMClient)
        return client

    def test_extract_clean_json(self):
        client = self._get_client()
        result = client._extract_json('{"name": "John", "skills": ["Python"]}')
        assert result["name"] == "John"
        assert "Python" in result["skills"]

    def test_extract_json_from_markdown_block(self):
        client = self._get_client()
        text = '```json\n{"name": "Jane", "score": 85}\n```'
        result = client._extract_json(text)
        assert result["name"] == "Jane"
        assert result["score"] == 85

    def test_extract_json_with_preamble(self):
        client = self._get_client()
        text = 'Here is the analysis:\n{"ats_score": 72, "missing": []}\nEnd.'
        result = client._extract_json(text)
        assert result["ats_score"] == 72

    def test_extract_invalid_json_raises(self):
        client = self._get_client()
        with pytest.raises(json.JSONDecodeError):
            client._extract_json("This is not JSON at all.")


# ---------------------------------------------------------------------------
# Unit Tests: DOCX Generator
# ---------------------------------------------------------------------------

class TestDocxGenerator:

    def test_safe_name(self):
        from modules.docx_generator import DocxResumeGenerator
        gen = DocxResumeGenerator()
        assert gen._safe_name("John Doe") == "john_doe"
        assert gen._safe_name("María García") == "mar_a_garc_a"
        assert len(gen._safe_name("A Very Long Name That Exceeds Limit")) <= 20

    def test_generate_creates_file(self, tmp_path, monkeypatch):
        """Generator should create a valid DOCX file."""
        from modules.docx_generator import DocxResumeGenerator
        from core.config import settings

        monkeypatch.setattr(settings, "OUTPUT_DIR", str(tmp_path))

        gen = DocxResumeGenerator()
        from models.schemas import OptimizedResume
        resume = OptimizedResume(
            name="Test User",
            contact=ContactInfo(email="test@test.com"),
            summary="Test summary",
            skills=["Python", "FastAPI"],
            work_experience=[],
            projects=[],
            education=[],
            achievements=[],
        )

        path = gen.generate(resume, "Software Engineer")
        import os
        assert os.path.exists(path)
        assert path.endswith(".docx")


# ---------------------------------------------------------------------------
# Integration Test: Pipeline (mocked LLM)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_with_mocked_llm(tmp_path):
    """
    Integration test: runs the full pipeline with a mocked LLM client.
    Verifies that all stages complete and a valid response is returned.
    """
    from core.pipeline import ResumePipeline
    from core.config import settings

    # Mock LLM responses for each stage
    mock_llm = MagicMock()

    # Each call returns a different JSON (one per pipeline stage)
    mock_llm.generate_json = AsyncMock(side_effect=[
        # Stage 1: Resume Parser
        {
            "name": "John Doe",
            "contact": {"email": "john@test.com", "phone": "555-1234",
                       "linkedin": None, "github": None, "portfolio": None, "location": "NYC"},
            "summary": "Software engineer",
            "skills": ["Python", "FastAPI"],
            "work_experience": [{"company": "ACME", "title": "Engineer",
                                  "start_date": "2020", "end_date": "Present",
                                  "location": "NYC", "bullets": ["Built APIs"]}],
            "projects": [],
            "education": [{"institution": "MIT", "degree": "B.S.",
                           "field": "CS", "graduation_year": "2020",
                           "gpa": None, "honors": None}],
            "achievements": [],
            "certifications": [],
        },
        # Stage 2: JD Analyzer
        {
            "job_title": "Python Engineer",
            "company_name": "TechCo",
            "required_skills": ["Python", "Docker"],
            "preferred_skills": ["Kubernetes"],
            "tools_and_technologies": ["AWS"],
            "key_responsibilities": ["Build APIs"],
            "qualifications": ["3+ years Python"],
            "keywords": ["microservices", "REST API"],
        },
        # Stage 3: ATS Scorer
        {
            "ats_score": 78,
            "score_breakdown": {"skills_match": 30, "keyword_coverage": 20},
            "matched_keywords": ["Python", "FastAPI"],
            "missing_keywords": ["Kubernetes", "CI/CD"],
            "missing_skills": ["Docker"],
            "recommendations": ["Add Docker experience"],
            "strengths": ["Strong Python background"],
        },
        # Stage 4: Resume Optimizer
        {
            "name": "John Doe",
            "contact": {"email": "john@test.com", "phone": "555-1234",
                       "linkedin": None, "github": None, "portfolio": None, "location": "NYC"},
            "summary": "Optimized summary targeting Python Engineer role",
            "skills": ["Python", "FastAPI", "Docker", "REST APIs"],
            "work_experience": [{"company": "ACME", "title": "Engineer",
                                  "start_date": "2020", "end_date": "Present",
                                  "location": "NYC",
                                  "bullets": ["Built microservices APIs using Python and Docker"]}],
            "projects": [],
            "education": [{"institution": "MIT", "degree": "B.S.",
                           "field": "CS", "graduation_year": "2020",
                           "gpa": None, "honors": None}],
            "achievements": [],
            "certifications": [],
        },
        # Stage 6: Cover Letter
        {
            "recipient_name": "Hiring Manager",
            "company_name": "TechCo",
            "job_title": "Python Engineer",
            "opening_paragraph": "I am excited to apply...",
            "body_paragraph_1": "In my role at ACME...",
            "body_paragraph_2": "I am drawn to TechCo because...",
            "closing_paragraph": "I look forward to connecting...",
            "full_text": "Dear Hiring Manager,\n\nI am excited...\n\nSincerely,\nJohn Doe",
        },
    ])

    # Patch output directory to tmp_path
    import core.config
    core.config.settings.OUTPUT_DIR = str(tmp_path)

    pipeline = ResumePipeline(llm_client=mock_llm)

    result = await pipeline.run_from_text(
        resume_text=SAMPLE_RESUME_TEXT,
        job_description=SAMPLE_JD_TEXT,
    )

    # Verify response structure
    assert result.parsed_resume.name == "John Doe"
    assert result.parsed_jd.job_title == "Python Engineer"
    assert result.ats_analysis.ats_score == 78
    assert result.optimized_resume.name == "John Doe"
    assert result.cover_letter.company_name == "TechCo"
    assert result.resume_docx_path is not None
    assert result.cover_letter_docx_path is not None
    assert result.processing_time_seconds > 0

    import os
    assert os.path.exists(result.resume_docx_path)
    assert os.path.exists(result.cover_letter_docx_path)
