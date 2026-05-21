"""
notification_agent.py
---------------------
Node 6 of the TenderMatch LangGraph pipeline.

Responsibilities:
  - Check if final_score >= score_threshold
  - If yes: dispatch send_match_notification_email Celery task
  - Persist final_match_result to MongoDB match_results collection
  - Populate: notification_sent, notification_skipped_reason, persisted
"""

import logging

from app.agents.state import TenderMatchState
from app.core.database import get_db

logger = logging.getLogger(__name__)

DEFAULT_SCORE_THRESHOLD = 70.0


async def notification_agent(state: TenderMatchState) -> dict:
    """
    LangGraph node: persist to MongoDB and optionally dispatch email notification.
    """
    logger.info("[Agent:Notification] START")

    final_match_result = state.get("final_match_result") or {}
    final_score = state.get("final_score", 0.0)
    match_id = state.get("match_id", "")
    threshold = state.get("score_threshold", DEFAULT_SCORE_THRESHOLD)

    # ── Persist to MongoDB match_results ──────────────────────────────────────
    persisted = False
    try:
        mongo_db = get_db()
        await mongo_db.match_results.replace_one(
            {"match_result._meta.match_id": match_id},
            final_match_result,
            upsert=True,
        )
        # Remove _id from in-memory state copy
        final_match_result.pop("_id", None)
        persisted = True
        logger.info("[Agent:Notification] ✓ Persisted match_id=%s", match_id)
    except Exception as exc:
        logger.error("[Agent:Notification] MongoDB persist failed: %s", exc)

    # ── Email notification (if score meets threshold) ─────────────────────────
    notification_sent = False
    notification_skipped_reason = None

    if final_score >= threshold:
        try:
            from app.tasks.notification_tasks import send_match_notification_email

            match_result_inner = final_match_result.get("match_result", {})
            vendor_id = match_result_inner.get("_meta", {}).get("vendor_id", "")
            explanation = match_result_inner.get("explanation", {})
            summary = explanation.get("executive_summary", "")
            recommendation = match_result_inner.get("recommendation", "")

            send_match_notification_email.delay(
                vendor_email=None,           # Will be resolved by the task from vendor_id
                vendor_name=vendor_id,
                tender_title=state.get("tender_structured_data", {}).get("scope_summary", "Tender Opportunity")[:80],
                match_score=final_score,
                explanation=summary or recommendation,
            )
            notification_sent = True
            logger.info(
                "[Agent:Notification] ✓ Email dispatched for vendor=%s score=%.1f",
                vendor_id, final_score,
            )
        except Exception as exc:
            logger.warning("[Agent:Notification] Email dispatch failed (non-fatal): %s", exc)
            notification_skipped_reason = f"Email dispatch failed: {exc}"
    else:
        notification_skipped_reason = (
            f"Score {final_score:.1f} below threshold {threshold:.1f}"
        )
        logger.info("[Agent:Notification] Email skipped. %s", notification_skipped_reason)

    return {
        "current_stage": "complete",
        "persisted": persisted,
        "notification_sent": notification_sent,
        "notification_skipped_reason": notification_skipped_reason,
        "final_match_result": final_match_result,
    }
