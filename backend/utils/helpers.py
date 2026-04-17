"""
Utility Helpers
===============
Shared utility functions used across pipeline modules.
"""

import re
import unicodedata
from typing import List


def clean_text(text: str) -> str:
    """
    Normalize and clean extracted text from PDFs/DOCX.
    Handles encoding issues, extra whitespace, special characters.
    """
    if not text:
        return ""

    # Normalize unicode (handles ligatures like ﬁ → fi)
    text = unicodedata.normalize("NFKD", text)

    # Replace common PDF extraction artifacts
    text = text.replace("\x00", "")       # Null bytes
    text = text.replace("\uf0b7", "•")    # PDF bullet character
    text = text.replace("\u2022", "•")    # Unicode bullet
    text = re.sub(r"\r\n|\r", "\n", text) # Normalize line endings

    # Collapse multiple blank lines to max 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove excessive spaces within lines
    lines = [re.sub(r" {3,}", "  ", line) for line in text.split("\n")]

    return "\n".join(lines).strip()


def truncate_text(text: str, max_chars: int = 8000) -> str:
    """Truncate text to fit within LLM context limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


def extract_filename(path: str) -> str:
    """Extract just the filename from a full path."""
    from pathlib import Path
    return Path(path).name


def normalize_skills(skills: List[str]) -> List[str]:
    """
    Deduplicate and normalize skill names.
    E.g., ['python', 'Python', 'PYTHON'] → ['Python']
    """
    seen = {}
    for skill in skills:
        normalized = skill.strip()
        key = normalized.lower()
        if key not in seen:
            seen[key] = normalized
    return list(seen.values())


def compute_keyword_overlap(text: str, keywords: List[str]) -> float:
    """
    Compute fraction of keywords that appear in text.
    Returns a float between 0.0 and 1.0.
    """
    if not keywords:
        return 0.0
    text_lower = text.lower()
    found = sum(1 for kw in keywords if kw.lower() in text_lower)
    return found / len(keywords)


def format_bullet(text: str) -> str:
    """
    Ensure bullet text is properly formatted.
    - Capitalize first letter
    - Remove leading bullet characters
    - Ensure no trailing period (ATS preference)
    """
    text = text.strip()
    # Remove leading bullet characters
    text = re.sub(r"^[•\-\*→▶►]\s*", "", text)
    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:]
    return text
