"""
tests/test_session_store.py
---------------------------
Unit tests for the in-memory session store's TTL eviction.

Run with:  pytest backend/tests/test_session_store.py
"""

import time

import pytest

import storage.session_store as store
from core.config import settings


@pytest.fixture(autouse=True)
def clean_store():
    """Start every test with empty stores and restore the TTL afterwards."""
    original_ttl = settings.job_retention_seconds
    for d in (store._job_statuses, store._job_results, store._job_jds,
              store._job_cvs, store._job_touched):
        d.clear()
    yield
    settings.job_retention_seconds = original_ttl


def test_idle_job_is_evicted_after_ttl():
    settings.job_retention_seconds = 0.05
    jid = store.create_job(total_cvs=2)
    assert store.get_status(jid) is not None

    time.sleep(0.1)
    assert store.sweep_expired() == 1

    # Evicted from every backing store, not just the status map.
    assert store.get_status(jid) is None
    assert jid not in store._job_results
    assert jid not in store._job_cvs
    assert jid not in store._job_touched


def test_active_job_survives_sweep():
    settings.job_retention_seconds = 3600
    jid = store.create_job(total_cvs=1)
    store.update_status(jid, status="processing", progress=20)

    assert store.sweep_expired() == 0
    assert store.get_status(jid) is not None


def test_update_status_resets_ttl_clock():
    settings.job_retention_seconds = 0.08
    jid = store.create_job(total_cvs=1)

    # Touch the job just before it would have expired — it should live on.
    time.sleep(0.05)
    store.update_status(jid, progress=50)
    time.sleep(0.05)
    assert store.sweep_expired() == 0
    assert store.get_status(jid) is not None


def test_create_job_sweeps_stale_jobs():
    settings.job_retention_seconds = 0.05
    stale = store.create_job(total_cvs=1)
    time.sleep(0.1)

    # Creating a new job triggers a sweep that should drop the stale one.
    store.create_job(total_cvs=1)
    assert store.get_status(stale) is None


def test_non_positive_ttl_disables_eviction():
    settings.job_retention_seconds = 0
    store.create_job(total_cvs=1)
    time.sleep(0.02)
    assert store.sweep_expired() == 0
