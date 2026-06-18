"""
core/groq_client.py
-------------------
Singleton wrapper around the Groq API (OpenAI-compatible SDK).

Provides:
  - chat_json()  → send a prompt, get a parsed dict back (structured output)
  - chat_text()  → send a prompt, get raw text back
"""

import json
import logging
from typing import Any, Optional

from groq import AsyncGroq
from core.config import settings

logger = logging.getLogger(__name__)

# Single shared client instance
_client: Optional[AsyncGroq] = None


def get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


def _extract_content(response: Any) -> str:
    """
    Safely pull the text content out of a Groq chat completion.

    The Groq/OpenAI API may return ``content == None`` (e.g. when the
    completion is empty, hit the content filter, or was cut off before any
    text was produced). Calling ``.strip()`` on that raises an opaque
    ``AttributeError``; instead we raise a clear, actionable error that names
    the ``finish_reason`` so callers can surface a useful message.
    """
    if not response.choices:
        raise ValueError("Groq returned no choices in the response.")

    choice = response.choices[0]
    content = choice.message.content

    if content is None:
        finish_reason = getattr(choice, "finish_reason", "unknown")
        logger.error("Groq returned empty content (finish_reason=%s)", finish_reason)
        raise ValueError(
            f"Groq returned no content (finish_reason={finish_reason}). "
            "The completion may have been blocked or truncated."
        )

    return content.strip()


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
    client = get_client()

    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    raw = _extract_content(response)
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
    client = get_client()

    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return _extract_content(response)
