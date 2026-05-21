import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Internal imports
from app.core.config import settings
from app.core.postgres import get_pg_session
from app.db.models.document import Tender, VendorProfile
from app.services.embedding_service import get_embedding_service

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
MONGO_URI = settings.MONGODB_URI
MONGO_DB_NAME = settings.DATABASE_NAME

# --- Test Data Design ---
# Vendor: Prajwal Kadam
# Domains: Smart City, CCTV, IT Infrastructure, Road Construction
# Locations: Maharashtra, Gujarat, Karnataka
# Turnover: ~12.5 Cr
# Certs: ISO 9001:2015, ISO 27001:2013, MNRE

TENDERS_TO_INSERT = [
    {
        "match_target": "92%",
        "title": "Smart City Command Center: CCTV & Network Infrastructure",
        "sector": "Smart City Projects",
        "location": "Pune, Maharashtra",
        "min_turnover": 20000000, # 2 Cr (High ratio)
        "min_experience_years": 1,
        "certifications": ["ISO 9001:2015"],
        "description": "Implementation of city-wide surveillance with AI analytics. Requires established vendors in Maharashtra with smart city experience.",
        "is_global": True
    },
    {
        "match_target": "80%",
        "title": "State Highway Expansion - Bituminous Works",
        "sector": "Road Construction",
        "location": "Ahmedabad, Gujarat",
        "min_turnover": 100000000, # 10 Cr (Ratio ~1.2)
        "min_experience_years": 5,
        "certifications": ["ISO 9001:2015", "ISO 14001"], # One missing
        "description": "Road widening and pavement construction for state highways. PWD Class A registration mandatory.",
        "is_global": True
    },
    {
        "match_target": "72%",
        "title": "Enterprise Networking & Data Center Maintenance",
        "sector": "IT Infrastructure",
        "location": "Bengaluru, Karnataka",
        "min_turnover": 120000000, # 12 Cr (Ratio ~1)
        "min_experience_years": 10, # Higher than vendor
        "certifications": ["ISO 27001:2013", "CCNA"], # One missing
        "description": "Maintenance of data center networking equipment and fiber connectivity. Support for virtualization and cloud infra.",
        "is_global": True
    },
    {
        "match_target": "50%",
        "title": "Procurement of Office Furniture and Interiors",
        "sector": "Interior Works", # Domain Mismatch (Score 0.3)
        "location": "Mumbai, Maharashtra", # Geo Match (Score 1.0)
        "min_turnover": 10000000, # Financial Match (Ratio 12.5 -> Score 1.0)
        "min_experience_years": 1,
        "certifications": [],
        "description": "Supply of modular workstations and office seating for government offices in Mumbai. Turnkey interior decoration services.",
        "is_global": True
    },
    {
        "match_target": "32%",
        "title": "Water Treatment Plant Construction - Ineligible",
        "sector": "Water Works", # Domain Mismatch (Score 0.3)
        "location": "Lucknow, UP", # Geo Ineligible (Score 0.5)
        "min_turnover": 500000000, # Financial Ineligible (Score 0.4)
        "min_experience_years": 5,
        "certifications": [],
        "description": "Design and construction of sewage treatment plants. Requires civil engineering background but turnover is far too high for this vendor.",
        "is_global": True # Makes it even more ineligible
    },
    {
        "match_target": "10%",
        "title": "Surgical Robotics Maintenance - Highly Ineligible",
        "sector": "Medical", 
        "location": "Imphal, Manipur",
        "min_turnover": 2000000000, 
        "min_experience_years": 15,
        "certifications": ["FDA Robotics"],
        "description": "Maintenance of Da Vinci surgical robots. Highly specialized medical certification required. Ineligible location and turnover.",
        "is_global": True
    },
    {
        "match_target": "0%",
        "title": "Nuclear Reactor Core Component Forging",
        "sector": "Nuclear Energy",
        "location": "Kalpakkam, Tamil Nadu",
        "min_turnover": 10000000000,
        "min_experience_years": 30,
        "certifications": ["AEC Class 1"],
        "description": "Manufacturing of high-precision components for nuclear reactors. Extreme turnover and experience requirements. No overlap with vendor capabilities.",
        "is_global": True
    }
]

async def insert_test_tenders():
    # 0. Initialize DB
    from app.core.postgres import init_postgres
    await init_postgres()
    
    # 1. Initialize services
    emb_svc = get_embedding_service()
    await emb_svc.warmup()
    
    mongo_client = AsyncIOMotorClient(MONGO_URI)
    mongo_db = mongo_client[MONGO_DB_NAME]
    
    logger.info("Connecting to databases...")
    
    # 2. Clear existing test tenders to avoid duplicates
    await mongo_db.documents.delete_many({"filename": {"$regex": "^test_tender_"}})
    async with get_pg_session() as session:
        from sqlalchemy import delete
        await session.execute(delete(Tender).where(Tender.filename.like("test_tender_%")))
        await session.commit()
    
    # 3. Get Org ID from the existing vendor profile to keep things tidy
    # Actually, the user's org_id from postgres
    async with get_pg_session() as session:
        # Assuming we just created Prajwal's profile
        result = await session.execute(
            select(VendorProfile).order_by(VendorProfile.created_at.desc()).limit(1)
        )
        vp = result.scalar_one_or_none()
        if not vp:
            logger.error("No Vendor Profile found. Please run fill_profile.py first.")
            return
        
        org_id = vp.org_id
        user_id = vp.user_id
        logger.info(f"Using Org ID: {org_id} from Vendor Profile: {vp.business_name}")

    # 3. Process and Insert Tenders
    for t_data in TENDERS_TO_INSERT:
        logger.info(f"Processing Tender: {t_data['title']} (Target: {t_data['match_target']})")
        
        # A. Prepare structured data for Mongo
        mongo_id_str = str(ObjectId())
        
        tender_doc = {
            "_id": ObjectId(mongo_id_str),
            "mongo_id": mongo_id_str, # Redundant but used in matching service
            "type": "tender",
            "status": "completed",
            "org_id": str(org_id),
            "uploaded_by": str(user_id),
            "is_global": t_data.get("is_global", True),
            "original_filename": f"test_tender_{t_data['match_target']}.pdf",
            "raw_text": t_data["description"] * 10, # Mock text
            "structured_data": {
                "title": t_data["title"],
                "sector": t_data["sector"],
                "location": t_data["location"],
                "min_turnover": t_data["min_turnover"],
                "min_experience_years": t_data["min_experience_years"],
                "certifications": t_data["certifications"],
                "submission_deadline": "2026-12-31T23:59:59Z",
                "estimated_value": t_data["min_turnover"] * 2
            },
            "keywords": [t_data["sector"], "Infrastructure", "Government"],
            "search_text": f"{t_data['title']} {t_data['sector']} {t_data['description']}",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # B. Insert into Mongo
        await mongo_db.documents.insert_one(tender_doc)
        
        # C. Generate Embedding
        embedding = await emb_svc.encode_text(tender_doc["search_text"])
        
        # D. Insert into Postgres
        async with get_pg_session() as session:
            pg_tender = Tender(
                mongo_id=mongo_id_str,
                org_id=org_id,
                filename=tender_doc["filename"],
                scope=t_data["description"],
                location=t_data["location"],
                embedding=embedding,
                summary={
                    "title": t_data["title"],
                    "sector": t_data["sector"],
                    "value": tender_doc["structured_data"]["estimated_value"]
                }
            )
            session.add(pg_tender)
            await session.commit()
            
        logger.info(f"Successfully inserted {t_data['title']} -> Mongo ID: {mongo_id_str}")

    logger.info("DONE! All test tenders inserted successfully.")

if __name__ == "__main__":
    asyncio.run(insert_test_tenders())
