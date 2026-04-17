"""
Core Configuration
==================
All environment-level settings loaded from .env via pydantic-settings.
Single source of truth for config across all modules.
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
import os



class Settings(BaseSettings):
    # -----------------------------------------------------------------------
    # LLM Provider Configuration
    # Supports: "huggingface" | "ollama" | "groq" (free tier)
    # -----------------------------------------------------------------------
    LLM_PROVIDER: str = Field(default="huggingface", description="LLM backend provider")

    # HuggingFace Inference API (free tier available)
 
 
    HF_API_TOKEN: str = Field(default="")
    HF_API_URL: str = Field(
        default="https://api-inference.huggingface.co/models",
        description="HuggingFace Inference API base URL",
    )
    LLM_MODEL: str = Field(
        default="mistralai/Mistral-7B-Instruct-v0.3",
        description="Model identifier (HF model ID or Ollama model name)",
    )

    # Ollama (local, fully open-source)
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL for local inference",
    )

    # Groq (free-tier cloud inference for open-source models)
    GROQ_API_KEY: str = Field(default="")
    GROQ_API_URL: str = Field(
        default="https://api.groq.com/openai/v1/chat/completions",
        description="Groq OpenAI-compatible endpoint",
    )
    GROQ_MODEL: str = Field(
        default="llama3-8b-8192",
        description="Groq model (llama3-8b-8192 is free)",
    )

    # -----------------------------------------------------------------------
    # LLM Inference Settings
    # -----------------------------------------------------------------------
    LLM_MAX_NEW_TOKENS: int = Field(default=2048, description="Max tokens to generate")
    LLM_TEMPERATURE: float = Field(default=0.3, description="Lower = more deterministic")
    LLM_TIMEOUT: int = Field(default=120, description="HTTP timeout in seconds")

    # -----------------------------------------------------------------------
    # File Upload Settings
    # -----------------------------------------------------------------------
    MAX_UPLOAD_SIZE_MB: int = Field(default=10, description="Max upload file size in MB")
    UPLOAD_DIR: str = Field(default="./uploads", description="Temp upload directory")
    OUTPUT_DIR: str = Field(default="./output", description="Generated files directory")
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=["pdf", "docx"], description="Allowed resume file types"
    )

    # -----------------------------------------------------------------------
    # CORS
    # -----------------------------------------------------------------------
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:5500",
            "https://*.github.io",   # GitHub Pages
            "*",                     # Set to specific domain in production
        ],
        description="Allowed CORS origins",
    )

    # -----------------------------------------------------------------------
    # App Settings
    # -----------------------------------------------------------------------
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton instance used across all modules
settings = Settings()
