"""
Resume Optimizer Module
========================
Stage 4 of the pipeline.

Responsibilities:
- Takes the original parsed resume + JD analysis + ATS gap report.
- Uses LLM to rewrite/optimize content to better match the JD.
- CRITICAL: Never fabricates experience. Only integrates keywords naturally.
- Returns an OptimizedResume ready for DOCX generation.
"""

import json
import logging

from core.llm_client import LLMClient
from models.schemas import (
    ATSAnalysis,
    OptimizedResume,
    ParsedJobDescription,
    ParsedResume,
    ContactInfo,
    WorkExperience,
    ProjectExperience,
    Education,
)
from prompts.templates import RESUME_OPTIMIZER_SYSTEM, RESUME_OPTIMIZER_USER

logger = logging.getLogger(__name__)


class ResumeOptimizer:
    """
    Optimizes resume content to maximize ATS score for a target role.

    Usage:
        optimizer = ResumeOptimizer(llm_client)
        optimized = await optimizer.optimize(parsed_resume, parsed_jd, ats_analysis)
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def optimize(
        self,
        parsed_resume: ParsedResume,
        parsed_jd: ParsedJobDescription,
        ats_analysis: ATSAnalysis,
    ) -> OptimizedResume:
        """Run resume optimization and return an OptimizedResume."""
        logger.info(f"Optimizing resume for: {parsed_jd.job_title}")

        # Serialize the parsed resume to JSON for the LLM
        resume_json = parsed_resume.model_dump_json(indent=2)

        user_prompt = RESUME_OPTIMIZER_USER.format(
            parsed_resume_json=resume_json[:5000],  # Truncate for token limit
            job_title=parsed_jd.job_title,
            required_skills=", ".join(parsed_jd.required_skills[:20]),
            missing_keywords=", ".join(ats_analysis.missing_keywords[:15]),
            responsibilities="\n".join(f"- {r}" for r in parsed_jd.key_responsibilities[:8]),
        )

        raw_json = await self.llm.generate_json(
            system_prompt=RESUME_OPTIMIZER_SYSTEM,
            user_prompt=user_prompt,
        )

        return self._json_to_optimized_resume(raw_json, parsed_resume)

    # -----------------------------------------------------------------------
    # JSON → OptimizedResume Model
    # -----------------------------------------------------------------------
    def _json_to_optimized_resume(self, data: dict, original: ParsedResume) -> OptimizedResume:
        """
        Convert LLM output to OptimizedResume.
        Falls back to original resume fields if LLM output is incomplete.
        """
        try:
            # Contact info - always use original (LLM should not change this)
            contact_data = data.get("contact", {}) or {}
            contact = ContactInfo(
                email=contact_data.get("email") or original.contact.email,
                phone=contact_data.get("phone") or original.contact.phone,
                linkedin=contact_data.get("linkedin") or original.contact.linkedin,
                github=contact_data.get("github") or original.contact.github,
                portfolio=contact_data.get("portfolio") or original.contact.portfolio,
                location=contact_data.get("location") or original.contact.location,
            )

            # Work experience - use LLM optimized, fall back to original
            work_exp = []
            llm_exp_list = data.get("work_experience", [])
            for i, exp in enumerate(llm_exp_list):
                if not isinstance(exp, dict):
                    continue
                # Get original experience for fallback
                orig_exp = original.work_experience[i] if i < len(original.work_experience) else None
                work_exp.append(WorkExperience(
                    company=exp.get("company") or (orig_exp.company if orig_exp else ""),
                    title=exp.get("title") or (orig_exp.title if orig_exp else ""),
                    start_date=exp.get("start_date") or (orig_exp.start_date if orig_exp else None),
                    end_date=exp.get("end_date") or (orig_exp.end_date if orig_exp else None),
                    location=exp.get("location") or (orig_exp.location if orig_exp else None),
                    bullets=[b for b in exp.get("bullets", []) if b],
                ))

            # If LLM returned no experience, use original
            if not work_exp:
                work_exp = original.work_experience

            # Projects - same fallback pattern
            projects = []
            for i, proj in enumerate(data.get("projects", [])):
                if not isinstance(proj, dict):
                    continue
                orig_proj = original.projects[i] if i < len(original.projects) else None
                projects.append(ProjectExperience(
                    name=proj.get("name") or (orig_proj.name if orig_proj else "Project"),
                    description=proj.get("description") or (orig_proj.description if orig_proj else None),
                    technologies=proj.get("technologies", []) or (orig_proj.technologies if orig_proj else []),
                    bullets=[b for b in proj.get("bullets", []) if b],
                    url=proj.get("url") or (orig_proj.url if orig_proj else None),
                ))

            if not projects:
                projects = original.projects

            # Education - always use original (don't let LLM modify these facts)
            education_list = []
            for edu in data.get("education", original.education):
                if isinstance(edu, dict):
                    education_list.append(Education(
                        institution=edu.get("institution", ""),
                        degree=edu.get("degree", ""),
                        field=edu.get("field"),
                        graduation_year=edu.get("graduation_year"),
                        gpa=edu.get("gpa"),
                        honors=edu.get("honors"),
                    ))

            if not education_list:
                education_list = original.education

            return OptimizedResume(
                name=data.get("name") or original.name,
                contact=contact,
                summary=data.get("summary") or original.summary or "",
                skills=data.get("skills") or original.skills,
                work_experience=work_exp,
                projects=projects,
                education=education_list,
                achievements=data.get("achievements") or original.achievements,
                certifications=data.get("certifications") or original.certifications,
            )

        except Exception as e:
            logger.error(f"Error converting optimizer output: {e}", exc_info=True)
            # Fallback: return original as OptimizedResume
            return OptimizedResume(
                name=original.name,
                contact=original.contact,
                summary=original.summary or "",
                skills=original.skills,
                work_experience=original.work_experience,
                projects=original.projects,
                education=original.education,
                achievements=original.achievements,
                certifications=original.certifications,
            )
