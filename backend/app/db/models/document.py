from sqlalchemy import Column, String, JSON, ForeignKey, DateTime, func, Text
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import uuid
from app.db.base import Base

class Tender(Base):
    __tablename__ = "tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mongo_id = Column(String(24), unique=True, index=True)  # Bridge to MongoDB
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), index=True)
    
    filename = Column(String(255))
    scope = Column(Text)
    location = Column(String(255))
    
    # Semantic data
    # all-MiniLM-L6-v2 uses 384 dimensions
    embedding = Column(Vector(384))
    
    # Metadata
    summary = Column(JSON)  # Stores certifications, keywords, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class VendorProfile(Base):
    __tablename__ = "vendor_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mongo_id = Column(String(24), unique=True, index=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    business_name = Column(String(255))
    
    # The vector representation of the vendor's capabilities
    embedding = Column(Vector(384))
    
    metadata_fields = Column(JSON)  # Industry, certifications, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
