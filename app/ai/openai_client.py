"""OpenAI API client with timeout, fallback, and rate controls."""

import logging
import re
import time
from datetime import datetime, timezone

from openai import AsyncOpenAI, APITimeoutError, APIError

from app.config import settings
from app.ai.prompts import REPORT_NARRATIVE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Rate control: track last request time and regeneration counts per session
_last_request_time: float = 0
_SESSION_COOLDOWN_SECONDS = 10

# Input sanitization limits
MAX_PROMPT_LENGTH = 8000
CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_input(text: str) -> str:
    """Strip control characters and enforce length limit."""
    text = CONTROL_CHAR_PATTERN.sub("", text)
    return text[:MAX_PROMPT_LENGTH]


def _get_client() -> AsyncOpenAI | None:
    """Create an AsyncOpenAI client if available."""
    if not settings.llm_available:
        return None
    return AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.OPENAI_TIMEOUT_MS / 1000,
    )


async def generate_narrative(user_prompt: str) -> dict:
    """Generate a report narrative using OpenAI.

    Returns: {"narrative": str, "model": str} or {"error": str}
    """
    global _last_request_time

    client = _get_client()
    if client is None:
        return {"error": "LLM features are not available"}

    # Rate control
    now = time.time()
    if now - _last_request_time < _SESSION_COOLDOWN_SECONDS:
        return {"error": f"Please wait {_SESSION_COOLDOWN_SECONDS} seconds between requests"}
    _last_request_time = now

    sanitized_prompt = _sanitize_input(user_prompt)
    models = [settings.OPENAI_MODEL]
    if settings.OPENAI_FALLBACK_MODEL != settings.OPENAI_MODEL:
        models.append(settings.OPENAI_FALLBACK_MODEL)

    for model in models:
        for attempt in range(settings.OPENAI_MAX_RETRIES + 1):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": REPORT_NARRATIVE_SYSTEM_PROMPT},
                        {"role": "user", "content": sanitized_prompt},
                    ],
                    max_tokens=1500,
                    temperature=0.7,
                )
                narrative = response.choices[0].message.content
                return {
                    "narrative": narrative,
                    "model": model,
                    "generatedAt": datetime.now(timezone.utc).isoformat(),
                }
            except APITimeoutError:
                logger.warning("OpenAI timeout with model %s (attempt %d)", model, attempt + 1)
                continue
            except APIError as e:
                logger.warning("OpenAI API error with model %s: %s", model, str(e))
                continue

    return {"error": "Failed to generate narrative after all attempts"}


async def check_llm_status() -> dict:
    """Check if LLM features are available."""
    return {
        "available": settings.llm_available,
        "model": settings.OPENAI_MODEL if settings.llm_available else None,
    }
