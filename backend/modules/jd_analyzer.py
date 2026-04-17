"""
Job Description Analyzer Module
=================================
Stage 2 of the pipeline.

Responsibilities:
- Parse raw job description text into structured requirements.
- Extract: required skills, preferred skills, tools, keywords, responsibilities.
- Returns a ParsedJobDescription model.
"""

import logging

from core.llm_client import LLMClient
from models.schemas import ParsedJobDescription
from prompts.templates import JD_ANALYZER_SYSTEM, JD_ANALYZER_USER

logger = logging.getLogger(__name__)


class JobDescriptionAnalyzer:
    """
    Analyzes job descriptions to extract structured requirements.

    Usage:
        analyzer = JobDescriptionAnalyzer(llm_client)
        jd = await analyzer.analyze("We are looking for a senior Python developer...")
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def analyze(self, job_description: str) -> ParsedJobDescription:
        """Parse raw JD text into a structured ParsedJobDescription object."""
        logger.info(f"Analyzing job description ({len(job_description)} chars)")

        user_prompt = JD_ANALYZER_USER.format(
            job_description=job_description[:6000]  # Truncate for token limit
        )

        raw_json = await self.llm.generate_json(
            system_prompt=JD_ANALYZER_SYSTEM,
            user_prompt=user_prompt,
        )

        return self._json_to_model(raw_json)

    def _json_to_model(self, data: dict) -> ParsedJobDescription:
        """Convert raw LLM JSON to a validated ParsedJobDescription."""
        try:
            return ParsedJobDescription(
                job_title=data.get("job_title", ""),
                company_name=data.get("company_name"),
                required_skills=self._ensure_list(data.get("required_skills", [])),
                preferred_skills=self._ensure_list(data.get("preferred_skills", [])),
                tools_and_technologies=self._ensure_list(data.get("tools_and_technologies", [])),
                key_responsibilities=self._ensure_list(data.get("key_responsibilities", [])),
                qualifications=self._ensure_list(data.get("qualifications", [])),
                keywords=self._ensure_list(data.get("keywords", [])),
            )
        except Exception as e:
            logger.error(f"Error converting JD JSON to model: {e}", exc_info=True)
            return ParsedJobDescription()

    @staticmethod
    def _ensure_list(value) -> list:
        """Normalize LLM output - sometimes returns a string instead of list."""
        if isinstance(value, list):
            return [str(v) for v in value if v]
        if isinstance(value, str):
            return [value] if value else []
        return []
