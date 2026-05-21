"""
weight_resolver.py
------------------
Service for resolving and normalizing learned vendor profile weights using a 
3-tier hierarchy: Vendor Profile -> Organization -> Global Defaults.
"""
from typing import Dict
import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import VendorProfileWeight

logger = logging.getLogger(__name__)

GLOBAL_DEFAULT_WEIGHTS = {
    "domain": 0.25,
    "geography": 0.15,
    "financial": 0.20,
    "experience": 0.15,
    "certification": 0.10,
    "semantic": 0.10,
    "confidence": 0.05
}

class WeightResolver:
    @staticmethod
    def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize a dictionary of weights so they sum to 1.0.
        Handles zero-sum by falling back to equal weighting.
        """
        total = sum(max(0.0, v) for v in weights.values())
        if total <= 0:
            # Fallback if somehow all weights hit 0 (should not happen with EMA properly clamped)
            n = len(weights)
            return {k: 1.0 / n for k in weights}
            
        return {k: max(0.0, v) / total for k, v in weights.items()}

    @classmethod
    async def get_weights(
        cls, 
        session: AsyncSession, 
        vendor_profile_id: str, 
        org_id: str = None
    ) -> Dict[str, float]:
        """
        Retrieve learned weights for the 7 scoring dimensions.
        Returns normalized weights ensuring the sum is exactly 1.0.
        """
        try:
            vp_uuid = uuid.UUID(vendor_profile_id)
        except (ValueError, TypeError):
            vp_uuid = None
            
        try:
            org_uuid = uuid.UUID(org_id) if org_id else None
        except (ValueError, TypeError):
            org_uuid = None

        if not vp_uuid and not org_uuid:
            return cls.normalize_weights(GLOBAL_DEFAULT_WEIGHTS)

        # Build query to fetch both profile and org weights simultaneously
        stmt = select(VendorProfileWeight).where(
            (VendorProfileWeight.vendor_profile_id == vp_uuid) | 
            (VendorProfileWeight.org_id == org_uuid)
        )
        result = await session.scalars(stmt)
        weights_records = result.all()

        profile_weight = None
        org_weight = None
        
        for w in weights_records:
            if w.vendor_profile_id == vp_uuid:
                profile_weight = w
            elif w.org_id == org_uuid and w.vendor_profile_id is None:
                org_weight = w

        # 1. Profile-level weights
        if profile_weight:
            w_dict = {
                "domain": profile_weight.weight_domain,
                "geography": profile_weight.weight_geography,
                "financial": profile_weight.weight_financial,
                "experience": profile_weight.weight_experience,
                "certification": profile_weight.weight_certification,
                "semantic": profile_weight.weight_semantic,
                "confidence": profile_weight.weight_confidence,
            }
            logger.debug(f"Using VendorProfile learned weights for {vendor_profile_id}")
            return cls.normalize_weights(w_dict)
            
        # 2. Org-level weights
        if org_weight:
            w_dict = {
                "domain": org_weight.weight_domain,
                "geography": org_weight.weight_geography,
                "financial": org_weight.weight_financial,
                "experience": org_weight.weight_experience,
                "certification": org_weight.weight_certification,
                "semantic": org_weight.weight_semantic,
                "confidence": org_weight.weight_confidence,
            }
            logger.debug(f"Using Org learned weights for {org_id}")
            return cls.normalize_weights(w_dict)

        # 3. Global defaults
        logger.debug("Using Global Default weights")
        return cls.normalize_weights(GLOBAL_DEFAULT_WEIGHTS)
