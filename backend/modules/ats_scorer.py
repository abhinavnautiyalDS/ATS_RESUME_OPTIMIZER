"""
ATS Scoring Engine
==================
Stage 3 of the pipeline.

Responsibilities:
- Compare parsed resume against parsed job description.
- Compute ATS compatibility score (0-100).
- Identify missing keywords and skills.
- Generate actionable recommendations.

Design: Hybrid approach:
  - Deterministic pre-scoring (keyword matching) for reliability.
  - LLM scoring for nuanced relevance analysis.
  - Final score combines both.
"""

import logging
from typing import List, Set

from core.llm_client import LLMClient
from models.schemas import ATSAnalysis, ParsedResume, ParsedJobDescription
from prompts.templates import ATS_ANALYZER_SYSTEM, ATS_ANALYZER_USER

logger = logging.getLogger(__name__)


class ATSScoringEngine:
    """
    Computes ATS compatibility between a resume and job description.

    Usage:
        engine = ATSScoringEngine(llm_client)
        analysis = await engine.analyze(parsed_resume, parsed_jd)
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def analyze(
        self,
        parsed_resume: ParsedResume,
        parsed_jd: ParsedJobDescription,
    ) -> ATSAnalysis:
        """Run full ATS gap analysis and return scored ATSAnalysis."""
        logger.info("Running ATS gap analysis...")

        # -----------------------------------------------------------------------
        # Step 1: Deterministic keyword matching (fast, no LLM needed)
        # -----------------------------------------------------------------------
        resume_text_lower = self._get_resume_text(parsed_resume).lower()
        jd_keywords = self._get_all_jd_keywords(parsed_jd)

        matched_keywords = [kw for kw in jd_keywords if kw.lower() in resume_text_lower]
        missing_keywords = [kw for kw in jd_keywords if kw.lower() not in resume_text_lower]

        resume_skills_lower = {s.lower() for s in parsed_resume.skills}
        jd_required_lower = {s.lower() for s in parsed_jd.required_skills}
        missing_skills = [s for s in parsed_jd.required_skills if s.lower() not in resume_skills_lower]

        # -----------------------------------------------------------------------
        # Step 2: LLM-powered semantic analysis
        # -----------------------------------------------------------------------
        user_prompt = ATS_ANALYZER_USER.format(
            name=parsed_resume.name,
            skills=", ".join(parsed_resume.skills[:30]),
            job_titles=", ".join(
                exp.title for exp in parsed_resume.work_experience[:5]
            ),
            summary=parsed_resume.summary or "Not provided",
            required_skills=", ".join(parsed_jd.required_skills[:20]),
            keywords=", ".join(parsed_jd.keywords[:20]),
            tools=", ".join(parsed_jd.tools_and_technologies[:15]),
        )

        raw_json = await self.llm.generate_json(
            system_prompt=ATS_ANALYZER_SYSTEM,
            user_prompt=user_prompt,
        )

        # -----------------------------------------------------------------------
        # Step 3: Merge deterministic + LLM results
        # -----------------------------------------------------------------------
        return self._build_analysis(raw_json, matched_keywords, missing_keywords, missing_skills)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    def _get_resume_text(self, resume: ParsedResume) -> str:
        """Concatenate all textual content from the resume for keyword search."""
        parts = [
            resume.name,
            resume.summary or "",
            " ".join(resume.skills),
            " ".join(resume.achievements),
        ]

        for exp in resume.work_experience:
            parts.extend([exp.title, exp.company] + exp.bullets)

        for proj in resume.projects:
            parts.extend([proj.name, proj.description or ""] + proj.bullets + proj.technologies)

        for edu in resume.education:
            parts.extend([edu.institution, edu.degree, edu.field or ""])

        return " ".join(filter(None, parts))

    def _get_all_jd_keywords(self, jd: ParsedJobDescription) -> List[str]:
        """Collect all meaningful terms from the job description."""
        all_terms: Set[str] = set()
        all_terms.update(jd.required_skills)
        all_terms.update(jd.preferred_skills)
        all_terms.update(jd.tools_and_technologies)
        all_terms.update(jd.keywords)
        # Filter out very short/common words
        return [t for t in all_terms if len(t) > 2]

    def _build_analysis(
        self,
        llm_data: dict,
        matched_keywords: List[str],
        missing_keywords: List[str],
        missing_skills: List[str],
    ) -> ATSAnalysis:
        """Merge LLM output with deterministic keyword analysis."""
        try:
            # Use LLM score if available, fall back to computed score
            ats_score = int(llm_data.get("ats_score", 50))
            ats_score = max(0, min(100, ats_score))  # Clamp to 0-100

            # Use deterministic matched/missing if LLM didn't provide them
            llm_matched = llm_data.get("matched_keywords", [])
            llm_missing = llm_data.get("missing_keywords", [])

            # Merge both sources (LLM adds semantic matching, we add exact matching)
            final_matched = list(set(matched_keywords + llm_matched))[:30]
            final_missing = list(set(missing_keywords + llm_missing))[:20]

            return ATSAnalysis(
                ats_score=ats_score,
                score_breakdown=llm_data.get("score_breakdown", {}),
                matched_keywords=final_matched,
                missing_keywords=final_missing,
                missing_skills=llm_data.get("missing_skills", missing_skills),
                recommendations=llm_data.get("recommendations", [])[:6],
                strengths=llm_data.get("strengths", [])[:4],
            )

        except Exception as e:
            logger.error(f"Error building ATS analysis: {e}", exc_info=True)
            # Return a basic analysis on error
            return ATSAnalysis(
                ats_score=50,
                matched_keywords=matched_keywords[:10],
                missing_keywords=missing_keywords[:10],
                missing_skills=missing_skills[:5],
                recommendations=["Review job requirements and update your skills section."],
                strengths=[],
            )
