"""
tests/test_groq_retry.py
------------------------
Unit tests for the Groq client's transient-failure retry policy.

Run with:  pytest backend/tests/test_groq_retry.py
"""

import asyncio
import types

import pytest

import core.groq_client as gc
from core.config import settings


@pytest.fixture(autouse=True)
def fast_retries():
    """Disable real backoff sleeps and reset the shared client."""
    original = (settings.groq_max_retries, settings.groq_retry_base_delay, gc._client)
    settings.groq_max_retries = 3
    settings.groq_retry_base_delay = 0
    yield
    (settings.groq_max_retries, settings.groq_retry_base_delay, gc._client) = original


def _fake_response(content):
    ns = types.SimpleNamespace
    return ns(choices=[ns(message=ns(content=content))])


def _rate_limit_error():
    return gc.RateLimitError(
        "rate limited",
        response=types.SimpleNamespace(status_code=429, request=None, headers={}),
        body=None,
    )


def test_retries_then_succeeds():
    calls = {"n": 0}

    async def create(**kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise _rate_limit_error()
        return _fake_response('{"ok": true}')

    ns = types.SimpleNamespace
    gc._client = ns(chat=ns(completions=ns(create=create)))

    out = asyncio.run(gc.chat_json("sys", "user"))
    assert out == {"ok": True}
    assert calls["n"] == 3  # two failures + one success


def test_exhausts_retries_then_raises():
    calls = {"n": 0}

    async def create(**kwargs):
        calls["n"] += 1
        raise gc.APIConnectionError(request=None)

    ns = types.SimpleNamespace
    gc._client = ns(chat=ns(completions=ns(create=create)))

    with pytest.raises(gc.APIConnectionError):
        asyncio.run(gc.chat_json("sys", "user"))
    assert calls["n"] == settings.groq_max_retries


def test_non_retryable_error_propagates_immediately():
    calls = {"n": 0}

    async def create(**kwargs):
        calls["n"] += 1
        raise ValueError("bad request")  # not in the retryable set

    ns = types.SimpleNamespace
    gc._client = ns(chat=ns(completions=ns(create=create)))

    with pytest.raises(ValueError):
        asyncio.run(gc.chat_text("sys", "user"))
    assert calls["n"] == 1  # no retries for non-transient errors
