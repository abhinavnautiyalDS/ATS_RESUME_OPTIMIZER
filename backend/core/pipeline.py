"""
Pipeline Orchestrator
=====================
Coordinates all stages of the ATS Resume Optimization pipeline.

Pipeline flow:
  File Upload
      ↓
  [Stage 1] Resume Parser     → ParsedResume
      ↓
  [Stage 2] JD Analyzer       → ParsedJobDescription
      ↓
  [Stage 3] ATS Scorer        → ATSAnalysis
      ↓
  [Stage 4] Resume Optimizer  → OptimizedResume
      ↓
  [Stage 5] DOCX Generator    → resume.docx
      ↓
  [Stage 6] Cover Letter Gen  → CoverLetter + cover_letter.docx
      ↓
  PipelineResponse (all data + file paths)

Design: Each stage is independent and can be tested in isolation.
        This orchestrator handles sequencing and error propagation.
"""

import logging
import time
from typing import Optional

from core.llm_client import LLMClient, get_llm_client
from models.schemas import PipelineResponse, ParsedResume
from modules.resume_parser import ResumeParser
from modules.jd_analyzer import JobDescriptionAnalyzer
from modules.ats_scorer import ATSScoringEngine
from modules.resume_optimizer import ResumeOptimizer
from modules.docx_generator import DocxResumeGenerator
from modules.cover_letter_generator import CoverLetterGenerator

logger = logging.getLogger(__name__)


class ResumePipeline:
    """
    Orchestrates the full ATS resume optimization pipeline.

    All stages are injected via the LLM client, making this
    testable and easily extensible.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or get_llm_client()

        # Initialize all pipeline modules
        self.resume_parser = ResumeParser(self.llm)
        self.jd_analyzer = JobDescriptionAnalyzer(self.llm)
        self.ats_scorer = ATSScoringEngine(self.llm)
        self.resume_optimizer = ResumeOptimizer(self.llm)
        self.docx_generator = DocxResumeGenerator()
        self.cover_letter_gen = CoverLetterGenerator(self.llm)

    async def run(
        self,
        file_bytes: bytes,
        filename: str,
        job_description: str,
    ) -> PipelineResponse:
        """
        Execute the full pipeline from file upload to generated documents.

        Args:
            file_bytes: Raw bytes of the uploaded resume file.
            filename: Original filename (used to determine file type).
            job_description: Raw text of the job description.

        Returns:
            PipelineResponse with all analysis data and file paths.
        """
        start_time = time.perf_counter()
        logger.info(f"=== Pipeline START | File: {filename} | JD length: {len(job_description)} ===")

        # -----------------------------------------------------------------------
        # Stage 1: Parse Resume
        # -----------------------------------------------------------------------
        logger.info("[Stage 1/6] Parsing resume...")
        stage_start = time.perf_counter()
        parsed_resume = await self.resume_parser.parse(file_bytes, filename)
        logger.info(f"  ✓ Resume parsed: {parsed_resume.name} | {len(parsed_resume.skills)} skills | {len(parsed_resume.work_experience)} jobs [{time.perf_counter()-stage_start:.2f}s]")

        # -----------------------------------------------------------------------
        # Stage 2: Analyze Job Description
        # -----------------------------------------------------------------------
        logger.info("[Stage 2/6] Analyzing job description...")
        stage_start = time.perf_counter()
        parsed_jd = await self.jd_analyzer.analyze(job_description)
        logger.info(f"  ✓ JD analyzed: {parsed_jd.job_title} | {len(parsed_jd.required_skills)} required skills [{time.perf_counter()-stage_start:.2f}s]")

        # -----------------------------------------------------------------------
        # Stage 3: ATS Gap Analysis
        # -----------------------------------------------------------------------
        logger.info("[Stage 3/6] Computing ATS score...")
        stage_start = time.perf_counter()
        ats_analysis = await self.ats_scorer.analyze(parsed_resume, parsed_jd)
        logger.info(f"  ✓ ATS score: {ats_analysis.ats_score}/100 | {len(ats_analysis.missing_keywords)} missing keywords [{time.perf_counter()-stage_start:.2f}s]")

        # -----------------------------------------------------------------------
        # Stage 4: Optimize Resume
        # -----------------------------------------------------------------------
        logger.info("[Stage 4/6] Optimizing resume content...")
        stage_start = time.perf_counter()
        optimized_resume = await self.resume_optimizer.optimize(
            parsed_resume, parsed_jd, ats_analysis
        )
        logger.info(f"  ✓ Resume optimized | {len(optimized_resume.skills)} skills in optimized version [{time.perf_counter()-stage_start:.2f}s]")

        # -----------------------------------------------------------------------
        # Stage 5: Generate Resume DOCX
        # -----------------------------------------------------------------------
        logger.info("[Stage 5/6] Generating DOCX resume...")
        stage_start = time.perf_counter()
        resume_docx_path = self.docx_generator.generate(optimized_resume, parsed_jd.job_title)
        logger.info(f"  ✓ Resume DOCX saved: {resume_docx_path} [{time.perf_counter()-stage_start:.2f}s]")

        # -----------------------------------------------------------------------
        # Stage 6: Generate Cover Letter + DOCX
        # -----------------------------------------------------------------------
        logger.info("[Stage 6/6] Generating cover letter...")
        stage_start = time.perf_counter()
        cover_letter, cover_letter_path = await self.cover_letter_gen.generate(
            optimized_resume, parsed_jd
        )
        logger.info(f"  ✓ Cover letter saved: {cover_letter_path} [{time.perf_counter()-stage_start:.2f}s]")

        # -----------------------------------------------------------------------
        # Assemble Response
        # -----------------------------------------------------------------------
        total_time = time.perf_counter() - start_time
        logger.info(f"=== Pipeline COMPLETE in {total_time:.2f}s ===")

        return PipelineResponse(
            parsed_resume=parsed_resume,
            parsed_jd=parsed_jd,
            ats_analysis=ats_analysis,
            optimized_resume=optimized_resume,
            cover_letter=cover_letter,
            resume_docx_path=resume_docx_path,
            cover_letter_docx_path=cover_letter_path,
            processing_time_seconds=round(total_time, 2),
        )

    async def run_from_text(
        self,
        resume_text: str,
        job_description: str,
    ) -> PipelineResponse:
        """
        Alternative entry point when resume is provided as text.
        Used for API testing and text-based inputs.
        """
        start_time = time.perf_counter()

        parsed_resume = await self.resume_parser.parse_from_text(resume_text)
        parsed_jd = await self.jd_analyzer.analyze(job_description)
        ats_analysis = await self.ats_scorer.analyze(parsed_resume, parsed_jd)
        optimized_resume = await self.resume_optimizer.optimize(parsed_resume, parsed_jd, ats_analysis)
        resume_docx_path = self.docx_generator.generate(optimized_resume, parsed_jd.job_title)
        cover_letter, cover_letter_path = await self.cover_letter_gen.generate(optimized_resume, parsed_jd)

        return PipelineResponse(
            parsed_resume=parsed_resume,
            parsed_jd=parsed_jd,
            ats_analysis=ats_analysis,
            optimized_resume=optimized_resume,
            cover_letter=cover_letter,
            resume_docx_path=resume_docx_path,
            cover_letter_docx_path=cover_letter_path,
            processing_time_seconds=round(time.perf_counter() - start_time, 2),
        )
