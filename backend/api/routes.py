"""
API Routes
==========
All FastAPI endpoints for the ATS Resume Optimizer.

Endpoints:
  POST /api/v1/optimize       - Main endpoint: upload resume + JD → all outputs
  POST /api/v1/optimize/text  - Text-based input (no file upload)
  GET  /api/v1/download/{id}  - Download generated DOCX files
  GET  /api/v1/status         - Service status and config info
"""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from core.config import settings
from core.pipeline import ResumePipeline
from models.schemas import PipelineRequest, PipelineResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Global pipeline instance (initialized once, reused across requests)
_pipeline: ResumePipeline | None = None


def get_pipeline() -> ResumePipeline:
    """Return the singleton pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = ResumePipeline()
    return _pipeline


# ---------------------------------------------------------------------------
# Main Endpoint: File Upload + Job Description
# ---------------------------------------------------------------------------
@router.post(
    "/optimize",
    response_model=PipelineResponse,
    summary="Optimize resume for a job description",
    description=(
        "Upload a resume (PDF or DOCX) and provide a job description. "
        "Returns parsed data, ATS score, optimized resume content, and download links for DOCX files."
    ),
    tags=["Pipeline"],
)
async def optimize_resume(
    resume_file: UploadFile = File(..., description="Resume file (PDF or DOCX, max 10MB)"),
    job_description: str = Form(..., description="Full text of the job description"),
):
    """
    Main pipeline endpoint.
    Accepts multipart/form-data with resume file + job description text.
    """
    # Validate file size
    file_bytes = await resume_file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Validate file extension
    filename = resume_file.filename or "resume.pdf"
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Validate job description length
    if len(job_description.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Job description is too short. Please provide the full job description.",
        )

    try:
        pipeline = get_pipeline()
        result = await pipeline.run(
            file_bytes=file_bytes,
            filename=filename,
            job_description=job_description,
        )
        return result

    except ValueError as e:
        logger.warning(f"Validation error in pipeline: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Pipeline runtime error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Pipeline failed. Please try again.")


# ---------------------------------------------------------------------------
# Text-Based Endpoint (No File Upload - for API testing)
# ---------------------------------------------------------------------------
@router.post(
    "/optimize/text",
    response_model=PipelineResponse,
    summary="Optimize resume from text input",
    description="Alternative endpoint for text-based resume input (no file upload required).",
    tags=["Pipeline"],
)
async def optimize_resume_text(request: PipelineRequest):
    """
    Text-based pipeline entry point.
    Useful for API testing, CI/CD, or programmatic usage.
    """
    try:
        pipeline = get_pipeline()
        result = await pipeline.run_from_text(
            resume_text=request.resume_text,
            job_description=request.job_description,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Text pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Pipeline failed.")


# ---------------------------------------------------------------------------
# Download Endpoint: Serve Generated DOCX Files
# ---------------------------------------------------------------------------
@router.get(
    "/download/{filename}",
    summary="Download a generated DOCX file",
    description="Download a generated resume or cover letter DOCX file by filename.",
    tags=["Downloads"],
)
async def download_file(filename: str):
    """
    Serve generated DOCX files for download.

    Security: Only files in the output directory are served.
    Path traversal is prevented by using Path.name only.
    """
    # Security: strip any path components - only allow plain filenames
    safe_filename = Path(filename).name
    if not safe_filename or ".." in safe_filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    filepath = Path(settings.OUTPUT_DIR) / safe_filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found or expired.")

    # Determine media type
    if safe_filename.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(filepath),
        media_type=media_type,
        filename=safe_filename,
    )


# ---------------------------------------------------------------------------
# Status Endpoint
# ---------------------------------------------------------------------------
@router.get(
    "/status",
    summary="Service status",
    tags=["Health"],
)
async def get_status():
    """Returns current service configuration and status."""
    return {
        "status": "operational",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "max_upload_mb": settings.MAX_UPLOAD_SIZE_MB,
        "allowed_extensions": settings.ALLOWED_EXTENSIONS,
        "output_dir": settings.OUTPUT_DIR,
    }
