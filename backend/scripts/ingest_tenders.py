import asyncio
import sys
from pymongo import MongoClient

# MongoDB connection
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "tendermatch"

tenders = [
    {
        "tender_id": "TW-2026-MAH-001",
        "domain": "Civil & Construction",
        "title": "NH-48 Phase 2 Highway Construction",
        "estimated_value": 4500000,
        "location_state": "Maharashtra",
        "min_avg_turnover": 1000000,
        "mandatory_certifications": [],
        "similar_work_definition": "Road and Highway Construction",
        "scope": "Extending the NH-48 highway corridor with multi-lane concrete roads in Pune district."
    },
    {
        "tender_id": "TW-2026-GUJ-002",
        "domain": "Civil & Construction",
        "title": "Ahmedabad Flyover Project",
        "estimated_value": 25000000,
        "location_state": "Gujarat",
        "min_avg_turnover": 5000000,
        "mandatory_certifications": [],
        "similar_work_definition": "Bridge and Flyover Construction",
        "scope": "Construction of a 2km flyover bridge over the Sabarmati river."
    },
    {
        "tender_id": "TW-2026-ASS-003",
        "domain": "IT & Software",
        "title": "State Portal Development",
        "estimated_value": 1500000,
        "location_state": "Assam",
        "min_avg_turnover": 500000,
        "mandatory_certifications": [],
        "similar_work_definition": "Software and Web Portal Development",
        "scope": "Development and maintenance of the new e-Governance portal for Assam state."
    },
    {
        "tender_id": "TW-2026-KER-004",
        "domain": "IT & Software",
        "title": "Network Infrastructure Setup",
        "estimated_value": 8000000,
        "location_state": "Kerala",
        "min_avg_turnover": 2000000,
        "mandatory_certifications": [],
        "similar_work_definition": "IT Hardware and Networking",
        "scope": "Supply and installation of networking switches and servers across 50 government schools."
    },
    {
        "tender_id": "TW-2026-FAIL-005",
        "domain": "Civil & Construction",
        "title": "High-speed Rail Track Laying",
        "estimated_value": 500000000,
        "location_state": "Maharashtra",
        "min_avg_turnover": 100000000,  # 100M > vendor's 50M -> should FAIL hard filter
        "mandatory_certifications": [],
        "similar_work_definition": "Metro and Rail track construction",
        "scope": "Laying of high-speed rail tracks for the bullet train corridor."
    },
    {
        "tender_id": "TW-2026-FAIL-006",
        "domain": "Civil & Construction",
        "title": "Military Bunker Construction",
        "estimated_value": 2000000,
        "location_state": "Maharashtra",
        "min_avg_turnover": 500000,
        "mandatory_certifications": ["Secret Clearance Certificate"], # Vendor missing this -> FAIL
        "similar_work_definition": "Defense Construction",
        "scope": "Construction of underground reinforced concrete bunkers."
    },
    {
        "tender_id": "TW-2026-PARTIAL-007",
        "domain": "Waste Management",
        "title": "City Waste Collection Services",
        "estimated_value": 3000000,
        "location_state": "Meghalaya",
        "min_avg_turnover": 0,
        "mandatory_certifications": [],
        "similar_work_definition": "Garbage and Waste Disposal",
        "scope": "Daily collection and transportation of solid waste to the municipal landfill."
    },
    {
        "tender_id": "TW-2026-MOD-008",
        "domain": "Civil & Construction",
        "title": "Rural Water Pipeline Construction",
        "estimated_value": 15000000,
        "location_state": "Tamil Nadu",
        "min_avg_turnover": 2000000,
        "mandatory_certifications": [],
        "similar_work_definition": "Water Supply and Pipeline Laying",
        "scope": "Laying of ductile iron pipes for drinking water supply in rural Tamil Nadu districts."
    },
    {
        "tender_id": "TW-2026-LOW-009",
        "domain": "Consulting",
        "title": "HR Training and Skill Development",
        "estimated_value": 500000,
        "location_state": "Bihar",
        "min_avg_turnover": 0,
        "mandatory_certifications": [],
        "similar_work_definition": "Corporate Training",
        "scope": "Conducting 2-week training workshops on modern HR practices."
    },
    {
        "tender_id": "TW-2026-OK-010",
        "domain": "IT & Software",
        "title": "CCTV Surveillance Installation",
        "estimated_value": 4500000,
        "location_state": "Maharashtra",
        "min_avg_turnover": 1000000,
        "mandatory_certifications": [],
        "similar_work_definition": "Security Systems and CCTV",
        "scope": "Installation of IP-based CCTV cameras and setting up a monitoring command center."
    }
]

def ingest():
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        # Clear existing to avoid duplicates in this demo
        db.tenders.delete_many({})
        print("Cleared existing tenders.")
        
        # Insert new
        result = db.tenders.insert_many(tenders)
        print(f"Successfully inserted {len(result.inserted_ids)} tenders into 'tendermatch.tenders' collection.")
        
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    ingest()
