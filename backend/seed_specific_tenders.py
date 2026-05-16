import asyncio
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# --- Configuration ---
MONGODB_URI = "mongodb://mongodb:27017"
POSTGRES_URI = "postgresql+asyncpg://tendermatch:changeme@postgres:5432/tendermatch"
DB_NAME = "tendermatch"

# TechBuild Profile Reference for alignment:
# Domains: IT & Software, Civil & Construction
# Turnover: 25 Cr
# Location: Maharashtra
# Certs: ISO 9001

SPECIFIC_TENDERS = [
    # --- 90%+ Matches (2 Tenders) ---
    {
        "title": "IT Infrastructure Upgrade - Mumbai Data Center",
        "sector": "IT & Software",
        "location": "Mumbai, Maharashtra",
        "value": 45000000, # 4.5 Cr
        "min_turnover": 8000000, # 0.8 Cr (Ratio > 5)
        "min_experience_years": 5,
        "certifications": ["ISO 9001"],
        "description": "Comprehensive upgrade of server infrastructure, cloud migration, and network security for a major government office in Mumbai.",
        "target_score": 95
    },
    {
        "title": "Smart City Software Implementation - Pune Phase II",
        "sector": "IT & Software",
        "location": "Pune, Maharashtra",
        "value": 30000000, # 3 Cr
        "min_turnover": 5000000, # 0.5 Cr
        "min_experience_years": 3,
        "certifications": ["ISO 9001:2015"],
        "description": "Development and deployment of smart traffic management systems and citizen portal using modern web technologies.",
        "target_score": 92
    },
    # --- 70% Matches (2 Tenders) ---
    {
        "title": "Bridge Maintenance & Rehabilitation - Karnataka Highway",
        "sector": "Civil & Construction",
        "location": "Bangalore, Karnataka",
        "value": 150000000, # 15 Cr
        "min_turnover": 100000000, # 10 Cr (Ratio 2.5)
        "min_experience_years": 12, # Tougher exp
        "certifications": ["ISO 14001"], # Mismatch certs
        "description": "Routine maintenance and structural strengthening of 3 bridges on the NH-48 stretch near Bangalore.",
        "target_score": 70
    },
    {
        "title": "Digital Literacy Program - Gujarat Schools",
        "sector": "IT & Software",
        "location": "Ahmedabad, Gujarat",
        "value": 120000000, # 12 Cr
        "min_turnover": 100000000, # 10 Cr
        "min_experience_years": 10,
        "certifications": ["CMMI Level 3"], # Mismatch certs
        "description": "Supply of IT hardware and training personnel for 500 rural schools across Gujarat.",
        "target_score": 70
    },
    # --- 50% - 59% Matches (2 Tenders) ---
    {
        "title": "Luxury Housing Complex - New Delhi",
        "sector": "Civil & Construction",
        "location": "New Delhi, Delhi", # Willing but not operational
        "value": 400000000, # 40 Cr (Turnover check fails)
        "min_turnover": 300000000, # 30 Cr (Vendor has 25 Cr)
        "min_experience_years": 15,
        "certifications": ["Green Building Council"],
        "description": "Construction of a premium residential tower with sustainability features in Central Delhi.",
        "target_score": 59
    },
    {
        "title": "Advanced AI Research Lab Setup - Hyderabad",
        "sector": "IT & Software",
        "location": "Hyderabad, Telangana",
        "value": 500000000, # 50 Cr
        "min_turnover": 400000000, # 40 Cr (Fails turnover)
        "min_experience_years": 20,
        "certifications": ["ISO 27001"],
        "description": "Setting up high-performance computing clusters and AI research environment for a national institute.",
        "target_score": 50
    }
]

async def seed_specific():
    print("🚀 Seeding specific tenders for targeted score ranges...")
    
    mongo_client = AsyncIOMotorClient(MONGODB_URI)
    db = mongo_client[DB_NAME]
    pg_engine = create_async_engine(POSTGRES_URI)

    # Mock embedding - in a real app, we'd use the embedding_service
    # Since we want them to appear in search, we'll give them semi-realistic mock vectors
    # (In this mock setup, any vector will be retrieved by our LIMIT 200 query)
    mock_vector = [0.1] * 384 

    for t in SPECIFIC_TENDERS:
        # 1. Insert into MongoDB
        mongo_doc = {
            "type": "tender",
            "is_global": True,
            "status": "completed",
            "title": t["title"],
            "description": t["description"],
            "structured_data": {
                "title": t["title"],
                "sector": t["sector"],
                "location": t["location"],
                "value": t["value"],
                "min_turnover": t["min_turnover"],
                "min_experience_years": t["min_experience_years"],
                "certifications": t["certifications"],
                "submission_deadline": "2026-12-31"
            },
            "created_at": datetime.utcnow()
        }
        res = await db.documents.insert_one(mongo_doc)
        mongo_id = str(res.inserted_id)
        
        # 2. Insert into PostgreSQL (pgvector)
        async with pg_engine.begin() as conn:
            # We use the same 'tenders' table
            query = text("""
                INSERT INTO tenders (id, mongo_id, filename, scope, location, embedding, summary)
                VALUES (:id, :mid, :fname, :scope, :loc, :vec, :summ)
            """)
            import json
            await conn.execute(query, {
                "id": uuid.uuid4(),
                "mid": mongo_id,
                "fname": f"specific_{mongo_id}.pdf",
                "scope": t["description"],
                "loc": t["location"],
                "vec": f"[{','.join(map(str, mock_vector))}]",
                "summ": json.dumps({"title": t["title"], "sector": t["sector"]})
            })
        
        print(f"✅ Created: {t['title']} (Target: {t['target_score']}%)")

    print("\n🎉 Seeding complete! These tenders are now ready for matching.")
    await pg_engine.dispose()
    mongo_client.close()

if __name__ == "__main__":
    asyncio.run(seed_specific())
