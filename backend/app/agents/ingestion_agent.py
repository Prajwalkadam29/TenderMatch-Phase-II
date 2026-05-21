"""
ingestion_agent.py
------------------
Node 1 of the TenderMatch LangGraph pipeline.

Responsibilities:
  - Load VendorProfile (profile_data JSONB + embedding) from PostgreSQL
  - Load tender document (structured_data + extraction_confidence) from MongoDB
  - Load tender vector embedding from PostgreSQL tenders bridge table
  - Populate: vendor_profile_data, vendor_embedding, tender_doc,
               tender_structured_data, tender_pg_embedding, extraction_confidence
"""

import uuid
import logging

import numpy as np
from sqlalchemy import select

from app.agents.state import TenderMatchState
from app.core.database import get_db
from app.core.postgres import get_pg_session
from app.db.models.document import VendorProfile, Tender

logger = logging.getLogger(__name__)


async def ingestion_agent(state: TenderMatchState) -> dict:
    """
    LangGraph node: loads vendor and tender data from all databases.

    On failure: sets state["error"] and state["error_stage"] so the
    graph's error edge can route to a safe terminal state.
    """
    logger.info("[Agent:Ingestion] START vendor=%s tender=%s",
                state.get("vendor_profile_id"), state.get("tender_mongo_id"))

    vendor_profile_id = state.get("vendor_profile_id", "")
    tender_mongo_id = state.get("tender_mongo_id", "")
    org_id = state.get("org_id")

    try:
        vp_uuid = uuid.UUID(vendor_profile_id)
    except ValueError:
        return {
            "error": f"Invalid vendor_profile_id: {vendor_profile_id}",
            "error_stage": "ingestion",
            "current_stage": "ingestion_failed",
        }

    # ── Load from PostgreSQL ──────────────────────────────────────────────────
    try:
        async with get_pg_session() as session:
            # Vendor
            q = select(VendorProfile).where(VendorProfile.id == vp_uuid)
            if org_id:
                try:
                    q = q.where(VendorProfile.org_id == uuid.UUID(org_id))
                except ValueError:
                    pass
            vendor_orm = await session.scalar(q)

            if not vendor_orm:
                return {
                    "error": f"VendorProfile not found: {vendor_profile_id}",
                    "error_stage": "ingestion",
                    "current_stage": "ingestion_failed",
                }

            # Tender vector bridge
            pg_tender = await session.scalar(
                select(Tender).where(Tender.mongo_id == tender_mongo_id)
            )
            
            from app.services.weight_resolver import WeightResolver
            custom_weights = await WeightResolver.get_weights(session, str(vendor_orm.id), str(vendor_orm.org_id) if vendor_orm.org_id else None)
    except Exception as exc:
        logger.error("[Agent:Ingestion] PostgreSQL fetch failed: %s", exc)
        return {
            "error": f"PostgreSQL error: {exc}",
            "error_stage": "ingestion",
            "current_stage": "ingestion_failed",
        }

    # ── Load from MongoDB ─────────────────────────────────────────────────────
    mongo_db = get_db()
    tender_doc = None

    try:
        tender_doc = await mongo_db.documents.find_one({"mongo_id": tender_mongo_id})
        if not tender_doc:
            from bson import ObjectId
            tender_doc = await mongo_db.documents.find_one({"_id": ObjectId(tender_mongo_id)})
    except Exception as exc:
        logger.error("[Agent:Ingestion] MongoDB fetch failed: %s", exc)
        return {
            "error": f"MongoDB error: {exc}",
            "error_stage": "ingestion",
            "current_stage": "ingestion_failed",
        }

    if not tender_doc:
        return {
            "error": f"Tender not found in MongoDB: {tender_mongo_id}",
            "error_stage": "ingestion",
            "current_stage": "ingestion_failed",
        }

    tender_embedding = None
    if pg_tender and pg_tender.embedding is not None:
        tender_embedding = list(pg_tender.embedding)

    logger.info(
        "[Agent:Ingestion] ✓ Loaded vendor=%s domain=%s",
        vendor_orm.vendor_id,
        (tender_doc.get("structured_data") or {}).get("domain"),
    )

    return {
        "current_stage": "ingestion_complete",
        "vendor_profile_data": vendor_orm.profile_data or {},
        "vendor_embedding": list(vendor_orm.embedding) if vendor_orm.embedding else None,
        "vendor_vendor_id": vendor_orm.vendor_id,
        "vendor_pg_uuid": str(vendor_orm.id),
        "tender_doc": tender_doc,
        "tender_structured_data": tender_doc.get("structured_data") or {},
        "tender_pg_embedding": tender_embedding,
        "extraction_confidence": float(tender_doc.get("extraction_confidence", 0.5)),
        "custom_weights": custom_weights,
    }
