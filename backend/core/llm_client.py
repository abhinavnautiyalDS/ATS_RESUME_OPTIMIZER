"""
LLM Client - Provider Abstraction Layer
========================================
Unified interface for multiple LLM backends.
Supports: HuggingFace Inference API, Ollama (local), Groq (free cloud).

Design: Strategy pattern - each provider implements the same interface.
This makes switching models/providers a single config change.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base LLM Provider Interface
# ---------------------------------------------------------------------------
class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a prompt and return the model's text response."""
        pass


# ---------------------------------------------------------------------------
# HuggingFace Inference API Provider
# ---------------------------------------------------------------------------
class HuggingFaceProvider(BaseLLMProvider):
    """
    Uses HuggingFace's free Inference API.
    Best for: mistralai/Mistral-7B-Instruct-v0.3, meta-llama/Llama-3-8B-Instruct
    Free tier: Rate limited but works for demos.
    """

    def __init__(self):
        self.api_url = f"{settings.HF_API_URL}/{settings.LLM_MODEL}"
        self.headers = {
            "Authorization": f"Bearer {settings.HF_API_TOKEN}",
            "Content-Type": "application/json",
        }

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        # Format as instruct-style prompt for Mistral/Llama
        prompt = f"<s>[INST] {system_prompt}\n\n{user_prompt} [/INST]"

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": settings.LLM_MAX_NEW_TOKENS,
                "temperature": settings.LLM_TEMPERATURE,
                "return_full_text": False,
                "do_sample": True,
            },
        }

        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            response = await client.post(self.api_url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()

        # HF returns a list of generated texts
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("generated_text", "")
        return str(data)


# ---------------------------------------------------------------------------
# Ollama Provider (Local, Fully Open-Source)
# ---------------------------------------------------------------------------
class OllamaProvider(BaseLLMProvider):
    """
    Uses Ollama for local model inference.
    Best for: llama3, mistral, phi3 - run `ollama pull llama3` first.
    No API key needed. Best privacy + no rate limits.
    """

    def __init__(self):
        self.api_url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        self.model = settings.LLM_MODEL  # e.g. "llama3" or "mistral"

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": settings.LLM_TEMPERATURE,
                "num_predict": settings.LLM_MAX_NEW_TOKENS,
            },
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            response = await client.post(self.api_url, json=payload)
            response.raise_for_status()
            data = response.json()

        return data["message"]["content"]


# ---------------------------------------------------------------------------
# Groq Provider (Free Cloud Inference for OSS Models)
# ---------------------------------------------------------------------------
class GroqProvider(BaseLLMProvider):
    """
    Uses Groq's free cloud API (OpenAI-compatible endpoint).
    Best for: llama3-8b-8192, mixtral-8x7b-32768
    Free tier: Very fast inference, generous rate limits.
    Get API key at: https://console.groq.com
    """

    def __init__(self):
        self.api_url = settings.GROQ_API_URL
        self.model = settings.GROQ_MODEL
        self.headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_NEW_TOKENS,
        }

        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            response = await client.post(self.api_url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# LLM Client - Main Interface Used by Pipeline
# ---------------------------------------------------------------------------
class LLMClient:
    """
    High-level LLM client used throughout the pipeline.
    Handles: provider selection, JSON extraction, retries, error logging.
    """

    def __init__(self):
        self.provider = self._initialize_provider()
        logger.info(f"LLM client initialized: {settings.LLM_PROVIDER} / {settings.LLM_MODEL}")

    def _initialize_provider(self) -> BaseLLMProvider:
        """Factory method: select provider based on config."""
        provider_map = {
            "huggingface": HuggingFaceProvider,
            "ollama": OllamaProvider,
            "groq": GroqProvider,
        }
        provider_class = provider_map.get(settings.LLM_PROVIDER.lower())
        if not provider_class:
            raise ValueError(
                f"Unknown LLM provider: {settings.LLM_PROVIDER}. "
                f"Choose from: {list(provider_map.keys())}"
            )
        return provider_class()

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3,
    ) -> dict:
        """
        Call the LLM and extract a JSON object from the response.
        Retries on invalid JSON up to max_retries times.
        """
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"LLM call attempt {attempt}/{max_retries}")
                raw_response = await self.provider.complete(system_prompt, user_prompt)
                logger.debug(f"Raw LLM response (first 300 chars): {raw_response[:300]}")

                # Extract JSON from the response (model sometimes adds prose around it)
                parsed = self._extract_json(raw_response)
                return parsed

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"JSON parse failed on attempt {attempt}: {e}")
                if attempt < max_retries:
                    # On retry, add stronger JSON instruction
                    user_prompt = user_prompt + "\n\nIMPORTANT: Return ONLY valid JSON, nothing else."
            except httpx.HTTPStatusError as e:
                logger.error(f"LLM API HTTP error: {e.response.status_code} - {e.response.text}")
                raise RuntimeError(f"LLM API error: {e.response.status_code}") from e
            except Exception as e:
                logger.error(f"LLM call failed: {e}", exc_info=True)
                raise

        raise ValueError(f"Failed to get valid JSON after {max_retries} attempts. Last error: {last_error}")

    def _extract_json(self, text: str) -> dict:
        """
        Robustly extract JSON from LLM response.
        Handles: wrapped in ```json...```, with preamble text, nested JSON.
        """
        # Strategy 1: Try to parse as-is (ideal case)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from markdown code block ```json ... ```
        code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if code_block:
            return json.loads(code_block.group(1))

        # Strategy 3: Find first { ... } block in the text
        brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if brace_match:
            return json.loads(brace_match.group(1))

        raise json.JSONDecodeError("No valid JSON found in LLM response", text, 0)


# ---------------------------------------------------------------------------
# Singleton LLM client (initialized once at startup)
# ---------------------------------------------------------------------------
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Dependency injection: returns the singleton LLM client."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
