import asyncio
import uuid
import logging
from datetime import datetime, timedelta, timezone
import numpy as np
from bson import ObjectId

from app.core.database import connect_to_mongo, get_db
from app.core.postgres import init_postgres, get_pg_session
from app.services.embedding_service import get_embedding_service
from app.db.models.document import Tender as PGTender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SeedGlobalTenders")

TENDERS_DATA = [
    {
        "title": "National Highway Expansion - Phase 4 (Civil Construction)",
        "department": "National Highways Authority",
        "sector": "Civil Construction",
        "country": "India",
        "state": "Maharashtra",
        "estimated_value": 500000000, 
        "min_turnover": 100000000,    
        "certs": ["ISO 9001", "ISO 14001", "Class A Contractor License"],
        "min_exp": 10,
        "keywords": ["highway", "bitumen", "earthworks", "bridge", "NHAI"],
        "scope": "Expansion of 4-lane highway to 6-lane including bridge construction, drainage, and utility shifting over 45km."
    },
    {
        "title": "Enterprise ERP Implementation (IT Software)",
        "department": "Ministry of Finance",
        "sector": "IT Software",
        "country": "India",
        "state": "Delhi",
        "estimated_value": 25000000,  
        "min_turnover": 5000000,     
        "certs": ["ISO 27001", "CMMI Level 5"],
        "min_exp": 5,
        "keywords": ["ERP", "SAP", "Oracle", "cloud migration", "finance module"],
        "scope": "Design, development and deployment of a centralized ERP system for financial tracking across 12 departments."
    },
    {
        "title": "City-wide Rooftop Solar Project (Solar Energy)",
        "department": "Renewable Energy Agency",
        "sector": "Solar Energy",
        "country": "India",
        "state": "Gujarat",
        "estimated_value": 80000000,  
        "min_turnover": 15000000,    
        "certs": ["MNRE Empanelment", "ISO 45001"],
        "min_exp": 3,
        "keywords": ["solar", "photovoltaic", "net metering", "rooftop", "renewable"],
        "scope": "Installation and maintenance of 5MW rooftop solar systems on government buildings in Ahmedabad."
    },
    {
        "title": "Multi-Speciality Hospital Equipment Supply",
        "department": "State Health Mission",
        "sector": "Healthcare",
        "country": "India",
        "state": "Karnataka",
        "estimated_value": 120000000, 
        "min_turnover": 30000000,    
        "certs": ["CE Certification", "ISO 13485", "NABH Accreditation"],
        "min_exp": 7,
        "keywords": ["MRI", "Ventilator", "Operation Theater", "Diagnostic", "Medical Device"],
        "scope": "Procurement and installation of critical medical equipment for the new government hospital in Bengaluru."
    },
    {
        "title": "Integrated Water Supply & Pipeline Project",
        "department": "Jal Jeevan Mission",
        "sector": "Water Infrastructure",
        "country": "India",
        "state": "Uttar Pradesh",
        "estimated_value": 350000000, 
        "min_turnover": 80000000,    
        "certs": ["BIS Certification", "Water Board Empanelment"],
        "min_exp": 8,
        "keywords": ["pipeline", "HDPE", "pump house", "purification", "water distribution"],
        "scope": "Laying of 120km distribution pipeline and construction of 5 overhead tanks for rural water supply."
    },
    {
        "title": "Railway Signaling & Modernization",
        "department": "Railways Board",
        "sector": "Railways",
        "country": "India",
        "state": "West Bengal",
        "estimated_value": 220000000, 
        "min_turnover": 50000000,    
        "certs": ["RDSO Approved", "ISO 9001"],
        "min_exp": 12,
        "keywords": ["signaling", "interlocking", "telecom", "track circuit", "modernization"],
        "scope": "Upgradation of signaling system to Electronic Interlocking (EI) across 15 stations in Howrah division."
    },
    {
        "title": "Secure Networking & Cybersecurity Infrastructure",
        "department": "Ministry of Defence",
        "sector": "Defence",
        "country": "India",
        "state": "Delhi",
        "estimated_value": 150000000, 
        "min_turnover": 40000000,    
        "certs": ["STQC Certified", "ISO 27001", "No-Blacklist Certificate"],
        "min_exp": 10,
        "keywords": ["cybersecurity", "firewall", "encrypted", "LAN/WAN", "defence network"],
        "scope": "Establishing a secure, encrypted internal network with 24/7 SOC monitoring for military headquarters."
    },
    {
        "title": "Smart Classroom & Digital Education Setup",
        "department": "Department of Education",
        "sector": "Education",
        "country": "India",
        "state": "Tamil Nadu",
        "estimated_value": 45000000,  
        "min_turnover": 10000000,    
        "certs": ["ISO 21001", "Hardware OEM Authorization"],
        "min_exp": 4,
        "keywords": ["smart class", "projector", "LMS", "interactive board", "digital content"],
        "scope": "Supply and installation of digital teaching kits for 500 government schools in Chennai region."
    },
    {
        "title": "CNC Machinery & Production Line Setup",
        "department": "Heavy Engineering Corp",
        "sector": "Manufacturing",
        "country": "India",
        "state": "Haryana",
        "estimated_value": 95000000,  
        "min_turnover": 25000000,    
        "certs": ["ISO 9001", "Safety Compliance"],
        "min_exp": 6,
        "keywords": ["CNC", "milling", "automation", "lathe", "precision engineering"],
        "scope": "Commissioning of automated CNC production line for precision aerospace components."
    },
    {
        "title": "Logistics & Fleet Tracking SaaS Solution",
        "department": "Postal Department",
        "sector": "Logistics",
        "country": "India",
        "state": "Pan India",
        "estimated_value": 30000000,  
        "min_turnover": 6000000,     
        "certs": ["ISO 27001", "GPS License"],
        "min_exp": 3,
        "keywords": ["fleet management", "GPS tracking", "SaaS", "logistics", "telematics"],
        "scope": "Implementation of a real-time tracking and route optimization platform for 2000 delivery vehicles."
    }
]

async def seed_global_tenders():
    await connect_to_mongo()
    await init_postgres()
    db = get_db()
    emb_svc = get_embedding_service()
    
    logger.info("Cleaning up old global tenders...")
    await db.documents.delete_many({"is_global": True})
    
    async with get_pg_session() as session:
        from sqlalchemy import delete
        # Postgres JSONB filtering
        await session.execute(delete(PGTender).where(PGTender.summary["is_global"].as_boolean() == True))
        await session.commit()

    for data in TENDERS_DATA:
        logger.info(f"Seeding Tender: {data['title']}")
        
        search_text = f"{data['title']} {data['sector']} {data['department']} {data['scope']} {' '.join(data['keywords'])}"
        embedding = await emb_svc.encode_text(search_text)
        
        mongo_id = str(ObjectId())
        now = datetime.now(timezone.utc)
        
        mongo_doc = {
            "mongo_id": mongo_id, # Redundant but good for indexing
            "type": "tender",
            "is_global": True,
            "original_filename": f"Global_Tender_{uuid.uuid4().hex[:6]}.pdf",
            "status": "completed",
            "search_text": search_text,
            "raw_text": search_text,
            "keywords": data["keywords"],
            "structured_data": {
                "title": data["title"],
                "department": data["department"],
                "sector": data["sector"],
                "location": f"{data['state']}, {data['country']}",
                "estimated_value": data["estimated_value"],
                "min_turnover": data["min_turnover"],
                "certifications": data["certs"],
                "min_experience_years": data["min_exp"],
                "scope": data["scope"],
                "submission_deadline": (now + timedelta(days=30)).isoformat()
            },
            "created_at": now,
            "updated_at": now
        }
        await db.documents.insert_one({**mongo_doc, "_id": ObjectId(mongo_id)})
        
        async with get_pg_session() as session:
            pg_tender = PGTender(
                mongo_id=mongo_id,
                filename=mongo_doc["original_filename"],
                scope=data["scope"],
                location=f"{data['state']}, {data['country']}",
                embedding=embedding,
                summary={
                    "title": data["title"],
                    "is_global": True,
                    "sector": data["sector"],
                    "estimated_value": data["estimated_value"],
                    "certifications": data["certs"]
                }
            )
            session.add(pg_tender)
            await session.commit()

    logger.info("Successfully seeded 10 Global Tenders.")

if __name__ == "__main__":
    asyncio.run(seed_global_tenders())
