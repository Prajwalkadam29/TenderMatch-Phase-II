from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.core.postgres import get_pg_session
from app.core.dependencies import require_role
from app.db.models.audit_log import AuditLog
from app.db.models.user import User

router = APIRouter(prefix="/activity", tags=["Activity"])

class ActivityOut(BaseModel):
    id: uuid.UUID
    action: str
    description: Optional[str]
    created_at: datetime
    actor_name: Optional[str]
    status: str

    class Config:
        from_attributes = True

@router.get("/organization", response_model=List[ActivityOut])
async def get_organization_activity(
    limit: int = Query(20, le=100),
    current_user: dict = Depends(require_role("ADMIN1", "SUPERADMIN"))
):
    """
    Fetch the latest audit logs for the current organization.
    Requires ADMIN1 or SUPERADMIN role.
    """
    org_id = current_user.get("org_id")
    if not org_id:
        return []

    # Since org_id in current_user is a string from Mongo, we need to handle it.
    # The audit_log.org_id was resolved during sync.
    # We'll look up by the actor's org if needed, but best to use the org_id field in audit_log.
    
    async with get_pg_session() as session:
        # Join with User to get actor names
        stmt = (
            select(
                AuditLog.id,
                AuditLog.action,
                AuditLog.description,
                AuditLog.created_at,
                AuditLog.status,
                User.name.label("actor_name")
            )
            .outerjoin(User, AuditLog.actor_id == User.id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        
        # Filter by org if provided
        # Note: If SUPERADMIN, they might want all or filtered by org. 
        # For now, we filter by the user's current org context.
        # AuditLog stores org_id as UUID (synced from Mongo).
        # We need to find the PG Organization first to get its UUID.
        from app.db.models.organization import Organization
        pg_org = await session.scalar(
            select(Organization).where(Organization.mongo_id == org_id)
        )
        
        if pg_org:
            stmt = stmt.where(AuditLog.org_id == pg_org.id)
        else:
            # Fallback: if org not synced to PG yet, return empty
            return []

        result = await session.execute(stmt)
        activities = []
        for row in result:
            activities.append({
                "id": row.id,
                "action": row.action,
                "description": row.description,
                "created_at": row.created_at,
                "actor_name": row.actor_name,
                "status": row.status
            })
            
        return activities


class DashboardSummary(BaseModel):
    total_tenders: int
    total_documents: int
    total_profiles: int
    recent_activity: List[ActivityOut]
    profile_completeness: Optional[float] = None
    top_matches_count: int = 0

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: dict = Depends(require_role("USER", "ADMIN1", "SUPERADMIN"))
):
    """
    Get a unified summary for the dashboard.
    """
    from app.core.database import get_db
    db = get_db()
    
    org_id = current_user.get("org_id")
    tenant_filter = {"org_id": org_id} if org_id else {"uploaded_by": str(current_user["_id"])}

    # 1. Basic Stats
    total_tenders = await db.documents.count_documents({"type": "tender", "status": "completed"})
    total_docs = await db.documents.count_documents(tenant_filter)
    total_profiles = await db.vendor_profiles.count_documents({"user_id": str(current_user["_id"])})

    # 2. Recent Activity (reusing logic but simplified)
    # For now, we'll return a few logs if possible, otherwise empty
    recent_logs = []
    try:
        # Re-using the logic from get_organization_activity but in a smaller scale
        recent_logs = await get_organization_activity(limit=5, current_user=current_user)
    except:
        pass

    # 3. Profile Completeness (from the most recently updated profile)
    profile_comp = 0.0
    latest_profile = await db.vendor_profiles.find_one(
        {"user_id": str(current_user["_id"])},
        sort=[("updated_at", -1)]
    )
    if latest_profile:
        profile_comp = latest_profile.get("completeness_score", 0.0)

    return DashboardSummary(
        total_tenders=total_tenders,
        total_documents=total_docs,
        total_profiles=total_profiles,
        recent_activity=recent_logs,
        profile_completeness=profile_comp,
        top_matches_count=0 # Placeholder until we have a real matching-count logic
    )
