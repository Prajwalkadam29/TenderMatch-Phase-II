"""
db/__init__.py
--------------
Imports all ORM models so Alembic's autogenerate can detect them.
Every new model file MUST be imported here.
"""

from app.db.base import Base  # noqa: F401

# Import all models — order matters for FK resolution
from app.db.models.organization import Organization  # noqa: F401
from app.db.models.user import User  # noqa: F401
from app.db.models.subscription import Subscription  # noqa: F401
from app.db.models.audit_log import AuditLog  # noqa: F401
from app.db.models.document import Tender, VendorProfile  # noqa: F401

__all__ = [
    "Base",
    "Organization",
    "User",
    "Subscription",
    "AuditLog",
    "Tender",
    "VendorProfile",
]
