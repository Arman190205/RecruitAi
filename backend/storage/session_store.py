"""
storage/session_store.py
------------------------
In-memory store for background job state and results.

Keyed by job_id (UUID). Holds:
  - JobStatus   → progress tracking
  - JobResult   → final ranked output
  - ParsedJD    → the JD used for scoring
  - List[ParsedCV] → all parsed candidates

Thread-safe for FastAPI's async context (single-process dev server).

Job state is retained only for ``settings.job_retention_seconds`` after its
last activity. Expired jobs are evicted lazily (swept whenever a new job is
created and on each status read), so a long-running server doesn't accumulate
state for every job it has ever processed.
"""

import logging
import time
import uuid
from typing import Optional

from core.config import settings
from models.result_models import JobStatus, JobResult
from models.jd_models import ParsedJD
from models.cv_models import ParsedCV

logger = logging.getLogger(__name__)


# ─── In-memory stores ─────────────────────────────────────────────────────────
_job_statuses: dict[str, JobStatus] = {}
_job_results:  dict[str, JobResult] = {}
_job_jds:      dict[str, ParsedJD]  = {}
_job_cvs:      dict[str, list[ParsedCV]] = {}
# job_id → monotonic timestamp of last activity (used for TTL eviction)
_job_touched:  dict[str, float] = {}


# ─── TTL eviction ─────────────────────────────────────────────────────────────

def _touch(job_id: str) -> None:
    """Record that a job was just created or updated (resets its TTL clock)."""
    _job_touched[job_id] = time.monotonic()


def _forget(job_id: str) -> None:
    """Drop all state for a single job across every store."""
    _job_statuses.pop(job_id, None)
    _job_results.pop(job_id, None)
    _job_jds.pop(job_id, None)
    _job_cvs.pop(job_id, None)
    _job_touched.pop(job_id, None)


def sweep_expired() -> int:
    """
    Evict every job whose last activity is older than the retention window.

    In-progress jobs are touched continuously by ``update_status`` during the
    pipeline, so they never expire mid-run — only idle (completed/failed) jobs
    age out. Returns the number of jobs evicted.
    """
    ttl = settings.job_retention_seconds
    if ttl <= 0:
        return 0
    cutoff = time.monotonic() - ttl
    # Snapshot keys first — we mutate the dicts inside the loop.
    expired = [jid for jid, ts in list(_job_touched.items()) if ts < cutoff]
    for jid in expired:
        _forget(jid)
    if expired:
        logger.info("Evicted %d expired job(s) from session store", len(expired))
    return len(expired)


# ─── Job creation ─────────────────────────────────────────────────────────────

def create_job(total_cvs: int) -> str:
    sweep_expired()
    job_id = str(uuid.uuid4())
    _job_statuses[job_id] = JobStatus(
        job_id=job_id,
        status="pending",
        progress=0,
        total_cvs=total_cvs,
    )
    _job_results[job_id] = JobResult(job_id=job_id)
    _job_cvs[job_id] = []
    _touch(job_id)
    return job_id


# ─── Status helpers ───────────────────────────────────────────────────────────

def get_status(job_id: str) -> Optional[JobStatus]:
    return _job_statuses.get(job_id)


def update_status(job_id: str, **kwargs) -> None:
    status = _job_statuses.get(job_id)
    if status:
        for key, value in kwargs.items():
            setattr(status, key, value)
        _touch(job_id)


def increment_progress(job_id: str) -> None:
    status = _job_statuses.get(job_id)
    if status and status.total_cvs > 0:
        status.processed_cvs += 1
        status.progress = int((status.processed_cvs / status.total_cvs) * 90)


# ─── JD helpers ───────────────────────────────────────────────────────────────

def store_jd(job_id: str, jd: ParsedJD) -> None:
    _job_jds[job_id] = jd
    _touch(job_id)


def get_jd(job_id: str) -> Optional[ParsedJD]:
    return _job_jds.get(job_id)


# ─── CV helpers ───────────────────────────────────────────────────────────────

def add_cv(job_id: str, cv: ParsedCV) -> None:
    _job_cvs.setdefault(job_id, []).append(cv)
    _touch(job_id)


def get_cvs(job_id: str) -> list[ParsedCV]:
    return _job_cvs.get(job_id, [])


# ─── Result helpers ───────────────────────────────────────────────────────────

def store_result(job_id: str, result: JobResult) -> None:
    _job_results[job_id] = result
    _touch(job_id)


def get_result(job_id: str) -> Optional[JobResult]:
    return _job_results.get(job_id)
