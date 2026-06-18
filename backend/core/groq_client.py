"""
core/groq_client.py
-------------------
Singleton wrapper around the Groq API (OpenAI-compatible SDK).

Provides:
  - chat_json()  → send a prompt, get a parsed dict back (structured output)
  - chat_text()  → send a prompt, get raw text back
"""

import asyncio
import json
import logging
from typing import Any, Optional

from groq import (
    AsyncGroq,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from core.config import settings

logger = logging.getLogger(__name__)

# Single shared client instance
_client: Optional[AsyncGroq] = None

# Errors that are worth retrying — transient infrastructure failures rather
# than bad requests. A 400/401/404 will never succeed on retry, so it is not
# listed here and propagates immediately.
_RETRYABLE_ERRORS = (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
)


def get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


async def _create_completion(system_prompt: str, user_prompt: str,
                             temperature: float, max_tokens: int):
    """
    Call the Groq chat-completions endpoint, retrying transient failures with
    exponential backoff (rate limits, connection drops, timeouts, 5xx).

    Retries up to ``settings.groq_max_retries`` times; non-retryable errors
    (e.g. 4xx) propagate immediately.
    """
    client = get_client()
    attempts = max(1, settings.groq_max_retries)

    for attempt in range(attempts):
        try:
            return await client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except _RETRYABLE_ERRORS as exc:
            if attempt == attempts - 1:
                logger.error("Groq call failed after %d attempts: %s", attempts, exc)
                raise
            delay = settings.groq_retry_base_delay * (2 ** attempt)
            logger.warning(
                "Groq call failed (attempt %d/%d): %s — retrying in %.1fs",
                attempt + 1, attempts, exc, delay,
            )
            await asyncio.sleep(delay)


async def chat_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    """
    Send a chat completion request and parse the response as JSON.

    The system prompt MUST instruct the model to reply with valid JSON only.
    Strips markdown code fences if present before parsing.
    """
    response = await _create_completion(system_prompt, user_prompt, temperature, max_tokens)

    raw = response.choices[0].message.content.strip()
    logger.debug("Groq raw response: %s", raw[:300])

    # Strip markdown code fences if the model wraps the JSON
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first and last fence lines
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Groq response as JSON: %s\nRaw: %s", exc, raw)
        raise ValueError(f"Groq did not return valid JSON: {exc}") from exc


async def chat_text(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str:
    """Send a chat completion request and return the raw text response."""
    response = await _create_completion(system_prompt, user_prompt, temperature, max_tokens)

    return response.choices[0].message.content.strip()
