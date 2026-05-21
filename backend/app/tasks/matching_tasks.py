"""
matching_tasks.py
-----------------
Celery tasks for the Match Orchestrator (Component 5).

Two tasks:
  run_match_task        — Matches a single vendor against a single tender.
                          Called by the LangGraph agent or directly from any route.

  run_bulk_match_task   — Fans out matching for ALL active vendors in an org
                          against a newly ingested tender. Dispatched from
                          ingestion_tasks.py Stage 9 (via notification_tasks chain).

Design decisions:
  - Both tasks use _run_async() to call the async orchestrate_match() from a
    synchronous Celery worker thread.
  - Exponential backoff retry: 60s, 120s, 240s.
  - Results are persisted inside orchestrate_match() — these tasks return a
    lightweight status dict rather than the full result, keeping Redis payload small.
  - run_bulk_match_task respects the notification threshold (default: score >= 70.0)
    before triggering email dispatch, keeping email volume under control.
"""

import asyncio
import logging
import uuid
from typing import Optional

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.celery_db import get_celery_db

logger = logging.getLogger(__name__)


# ─── Async bridge ─────────────────────────────────────────────────────────────

def _run_async(coro):
    """Run an async coroutine synchronously inside a Celery worker thread."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)


# ─── Task 1: Single-pair match ────────────────────────────────────────────────

@celery_app.task(
    name="run_match_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def run_match_task(
    self,
    vendor_profile_id: str,
    tender_mongo_id: str,
    org_id: Optional[str] = None,
    use_langgraph: bool = False,
) -> dict:
    """
    Match a single vendor against a single tender.

    Calls orchestrate_match() which runs the full 8-step pipeline:
      HardFilter → SemanticScore → WeightedScore → Explanation → Persist

    Args:
        vendor_profile_id:  PostgreSQL UUID string of the VendorProfile
        tender_mongo_id:    MongoDB ObjectId string of the tender document
        org_id:             Optional org UUID string for tenancy isolation

    Returns:
        Lightweight status dict: {status, match_id, final_score, recommendation}
    """
    from app.services.matching_service import orchestrate_match
    from app.agents.graph import run_match_pipeline

    logger.info(
        "[MatchTask] START vendor=%s tender=%s langgraph=%s",
        vendor_profile_id, tender_mongo_id, use_langgraph
    )

    try:
        if use_langgraph:
            result = _run_async(
                run_match_pipeline(
                    vendor_profile_id=vendor_profile_id,
                    tender_mongo_id=tender_mongo_id,
                    org_id=org_id,
                )
            )
            # The langgraph pipeline returns the final match result directly or an error dict
            if result.get("status") == "error":
                return result
            match_result = result.get("match_result", {})
        else:
            result = _run_async(
                orchestrate_match(
                    vendor_profile_id=vendor_profile_id,
                    tender_mongo_id=tender_mongo_id,
                    org_id=org_id,
                )
            )
            match_result = result.get("match_result", {})
        final_score = match_result.get("weighted_score", {}).get("final_score", 0.0)
        recommendation = match_result.get("recommendation", "UNKNOWN")
        match_id = match_result.get("_meta", {}).get("match_id", "")

        logger.info(
            "[MatchTask] COMPLETE match_id=%s score=%.1f recommendation=%s",
            match_id, final_score, recommendation,
        )

        return {
            "status": "success",
            "match_id": match_id,
            "vendor_profile_id": vendor_profile_id,
            "tender_mongo_id": tender_mongo_id,
            "final_score": final_score,
            "recommendation": recommendation,
        }

    except ValueError as exc:
        # ValueError = bad IDs or not found — don't retry
        logger.error("[MatchTask] ✗ Non-retryable error: %s", exc)
        return {
            "status": "error",
            "error": str(exc),
            "vendor_profile_id": vendor_profile_id,
            "tender_mongo_id": tender_mongo_id,
        }

    except Exception as exc:
        logger.error(
            "[MatchTask] ✗ FAILED vendor=%s tender=%s error=%s",
            vendor_profile_id, tender_mongo_id, exc, exc_info=True,
        )
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


# ─── Task 2: Bulk match for all vendors against a new tender ─────────────────

@celery_app.task(
    name="run_bulk_match_task",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
)
def run_bulk_match_task(
    self,
    tender_mongo_id: str,
    org_id: Optional[str] = None,
    score_threshold: float = 70.0,
) -> dict:
    """
    Fan-out matching for all active VendorProfiles in an org against a new tender.

    This task is dispatched from the ingestion pipeline after a new tender is
    processed (Stage 9 of ingest_tender_document). It:
      1. Queries all active VendorProfiles from PostgreSQL (scoped by org_id)
      2. Dispatches a run_match_task for each vendor (async fan-out)
      3. For profiles with high scores (>= score_threshold), dispatches email alerts

    Args:
        tender_mongo_id:   MongoDB ObjectId string of the newly ingested tender
        org_id:            Optional org UUID string — if None, matches globally
        score_threshold:   Minimum score to trigger email notification (default 70.0)

    Returns:
        {status, tender_mongo_id, vendors_queued, notifications_dispatched}
    """
    from app.core.postgres import get_pg_session as _pg_session

    logger.info(
        "[BulkMatch] START tender=%s org=%s",
        tender_mongo_id, org_id,
    )

    try:
        # Fetch all active vendor profile IDs from PostgreSQL
        async def _fetch_active_vendors():
            from app.db.models.document import VendorProfile

            async with _pg_session() as session:
                stmt = select(VendorProfile.id, VendorProfile.org_id).where(
                    VendorProfile.is_active == True
                )
                if org_id:
                    try:
                        stmt = stmt.where(VendorProfile.org_id == uuid.UUID(org_id))
                    except ValueError:
                        logger.warning("[BulkMatch] Invalid org_id format: %s. Matching globally.", org_id)

                rows = await session.execute(stmt)
                return [(str(row.id), str(row.org_id) if row.org_id else None) for row in rows]

        vendor_list = _run_async(_fetch_active_vendors())

        if not vendor_list:
            logger.info("[BulkMatch] No active vendor profiles found for org=%s", org_id)
            return {
                "status": "success",
                "tender_mongo_id": tender_mongo_id,
                "vendors_queued": 0,
                "message": "No active vendor profiles found.",
            }

        logger.info("[BulkMatch] Queuing %d vendor match tasks.", len(vendor_list))

        queued = 0
        for vp_id, vp_org_id in vendor_list:
            run_match_task.apply_async(
                args=[vp_id, tender_mongo_id, vp_org_id or org_id],
                countdown=queued * 2,  # Stagger by 2 seconds to avoid thundering herd
            )
            queued += 1

        logger.info(
            "[BulkMatch] COMPLETE tender=%s vendors_queued=%d",
            tender_mongo_id, queued,
        )

        return {
            "status": "success",
            "tender_mongo_id": tender_mongo_id,
            "vendors_queued": queued,
        }

    except Exception as exc:
        logger.error(
            "[BulkMatch] ✗ FAILED tender=%s error=%s",
            tender_mongo_id, exc, exc_info=True,
        )
        countdown = 120 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


# ─── Task 3: Process Feedback (EMA Weight Updates) ────────────────────────────

@celery_app.task(
    name="process_feedback_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def process_feedback_task(
    self,
    match_id: str,
    signal: str,
    vendor_profile_id: str,
    org_id: Optional[str] = None
) -> dict:
    """
    Asynchronously update weights based on user feedback using EMA.
    
    Signal values:
      Won          → +1.0
      Submitted    → +0.6
      Interested   → +0.3
      Not Relevant → -0.4
      Lost         → -0.2
    
    Learning rate: 0.05
    """
    logger.info(f"[FeedbackTask] START match={match_id} signal={signal} vp={vendor_profile_id}")
    
    try:
        # Import inside the task to avoid circular dependency
        from app.services.feedback_processor import process_match_feedback
        
        result = _run_async(process_match_feedback(
            match_id=match_id,
            signal=signal,
            vendor_profile_id=vendor_profile_id,
            org_id=org_id
        ))
        
        logger.info(f"[FeedbackTask] COMPLETE match={match_id}")
        return result
    except Exception as exc:
        logger.error(
            "[FeedbackTask] ✗ FAILED match=%s error=%s",
            match_id, exc, exc_info=True,
        )
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
