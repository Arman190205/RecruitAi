"""
services/ranker.py
------------------
Feature 3: Full scoring pipeline orchestrator.

Called as a FastAPI BackgroundTask after CV upload.

Pipeline:
  1. For each uploaded file:
       a. Extract raw text (cv_extractor)
       b. Parse into ParsedCV (cv_parser)
       c. Store in session_store + update progress
  2. Score each ParsedCV against the stored ParsedJD (scorer)
  3. Sort by total score descending, assign ranks 1..N
  4. Store final JobResult; set job status → "completed"

If an error occurs at any point, the job status is set to "failed".
Individual CV parse errors are captured and do not abort the batch.
"""

import asyncio
import logging
import time
from core.config import settings
from models.cv_models import CVUploadStatus
from models.result_models import JobResult, CandidateResult
from services.cv_extractor import extract_text
from services.cv_parser import parse_cv
from services.scorer import score_candidate
from services.bias_detector import detect_bias
import storage.session_store as store

logger = logging.getLogger(__name__)


async def run_scoring_pipeline(
    job_id: str,
    files: list[tuple[str, bytes]],  # (filename, raw_bytes)
) -> None:
    """
    Background pipeline with a hard wall-clock budget.

    Delegates to :func:`_scoring_pipeline_impl` under ``asyncio.wait_for`` so a
    stalled LLM call (or any other hang) can't leave a job stuck "processing"
    forever — it is cancelled and marked "failed" once the budget is exceeded.
    Set ``processing_timeout_seconds`` to 0 to disable the timeout.
    """
    timeout = settings.processing_timeout_seconds
    timeout = timeout if timeout and timeout > 0 else None
    try:
        await asyncio.wait_for(_scoring_pipeline_impl(job_id, files), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error("[Job %s] Pipeline timed out after %ss — marking failed",
                     job_id, timeout)
        store.update_status(
            job_id, status="failed",
            error=f"Processing timed out after {timeout}s. Try fewer or smaller files.",
        )
    except Exception as exc:  # noqa: BLE001 — last-resort guard for a background task
        logger.exception("[Job %s] Pipeline crashed: %s", job_id, exc)
        store.update_status(job_id, status="failed", error=str(exc))


async def _scoring_pipeline_impl(
    job_id: str,
    files: list[tuple[str, bytes]],  # (filename, raw_bytes)
) -> None:
    """
    Background pipeline: parse CVs → score → rank → store results.

    Args:
        job_id: UUID of the job created by the upload endpoint.
        files:  List of (filename, bytes) tuples from the upload.
    """
    start_time = time.perf_counter()
    logger.info("[Job %s] Pipeline started — %d files", job_id, len(files))

    store.update_status(job_id, status="processing", progress=0)

    # ── Phase 1: Extract & Parse CVs ─────────────────────────────────────────
    cv_statuses: list[CVUploadStatus] = []
    for filename, _ in files:
        cv_statuses.append(CVUploadStatus(filename=filename, status="pending"))
    store.update_status(job_id, cv_statuses=cv_statuses, progress=0)

    sem = asyncio.Semaphore(3)
    completed_parses = 0

    async def parse_file_worker(idx: int, filename: str, file_bytes: bytes):
        nonlocal completed_parses
        status_entry = cv_statuses[idx]
        status_entry.status = "processing"
        store.update_status(job_id, cv_statuses=cv_statuses)

        try:
            # 1a. Extract raw text
            raw_text = extract_text(filename, file_bytes)

            # 1b. Parse with LLM
            import uuid
            candidate_id = str(uuid.uuid4())
            async with sem:
                cv = await parse_cv(filename, raw_text, candidate_id)

            # 1c. Store parsed CV
            store.add_cv(job_id, cv)
            status_entry.status = "done"

        except Exception as exc:
            logger.error("[Job %s] Failed to process '%s': %s", job_id, filename, exc)
            status_entry.status = "error"
            status_entry.error = str(exc)

        completed_parses += 1
        # Update progress after each file (Phase 1 = 0–50%)
        progress = int((completed_parses / len(files)) * 50)
        store.update_status(job_id, cv_statuses=cv_statuses, progress=progress, processed_cvs=completed_parses)

    # Run parses in parallel
    parse_tasks = [
        parse_file_worker(idx, filename, file_bytes)
        for idx, (filename, file_bytes) in enumerate(files)
    ]
    await asyncio.gather(*parse_tasks)

    parsed_cvs = store.get_cvs(job_id)
    jd = store.get_jd(job_id)

    if not parsed_cvs:
        logger.error("[Job %s] No CVs were successfully parsed. Aborting.", job_id)
        store.update_status(job_id, status="failed",
                            error="No CVs could be parsed successfully.")
        return

    if jd is None:
        logger.error("[Job %s] No JD found in store. Aborting.", job_id)
        store.update_status(job_id, status="failed", error="JD not found.")
        return

    # ── Phase 2: Score each candidate ────────────────────────────────────────
    cvs_to_score = [cv for cv in parsed_cvs if not cv.parse_error]
    total_to_score = len(cvs_to_score)

    logger.info("[Job %s] Scoring %d candidates...", job_id, total_to_score)
    candidate_results: list[CandidateResult] = []
    completed_scorings = 0

    async def score_cv_worker(cv):
        nonlocal completed_scorings
        try:
            async with sem:
                result = await score_candidate(cv, jd)
            candidate_results.append(result)
        except Exception as exc:
            logger.error("[Job %s] Scoring failed for '%s': %s",
                         job_id, cv.filename, exc)

        completed_scorings += 1
        # Update progress (Phase 2 = 50–90%)
        if total_to_score > 0:
            progress = 50 + int((completed_scorings / total_to_score) * 40)
            store.update_status(job_id, progress=progress)

    if total_to_score > 0:
        score_tasks = [score_cv_worker(cv) for cv in cvs_to_score]
        await asyncio.gather(*score_tasks)
    else:
        store.update_status(job_id, progress=90)

    # ── Phase 3: Rank candidates ──────────────────────────────────────────────
    ranked = sorted(candidate_results,
                    key=lambda r: r.score_breakdown.total,
                    reverse=True)
    ranked = ranked[:settings.top_n_candidates]
    for i, candidate in enumerate(ranked, start=1):
        candidate.rank = i

    # ── Phase 4: Run bias / diversity check ───────────────────────────────────
    bias_report = detect_bias(ranked)

    elapsed = round(time.perf_counter() - start_time, 2)

    # ── Phase 5: Store final result ───────────────────────────────────────────
    job_result = JobResult(
        job_id=job_id,
        jd=jd,
        ranked_candidates=ranked,
        bias_report=bias_report,
        total_screened=len(parsed_cvs),
        processing_time_seconds=elapsed,
    )
    store.store_result(job_id, job_result)
    store.update_status(job_id, status="completed", progress=100,
                        cv_statuses=cv_statuses)

    logger.info(
        "[Job %s] Pipeline complete — %d ranked in %.2fs",
        job_id, len(ranked), elapsed,
    )
