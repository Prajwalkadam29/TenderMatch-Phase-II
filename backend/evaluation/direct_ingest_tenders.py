import json
import os
import uuid
from datetime import datetime, timezone
from pymongo import MongoClient
import psycopg2
from sentence_transformers import SentenceTransformer

def direct_ingest():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    
    # 1. Connect to Mongo
    mongo_client = MongoClient("mongodb://localhost:27018/")
    mongo_db = mongo_client["tendermatch"]
    
    # 2. Connect to Postgres
    pg_conn = psycopg2.connect("postgresql://tendermatch:changeme@localhost:5433/tendermatch")
    pg_cursor = pg_conn.cursor()
    
    # Get Organization ID for eval user
    pg_cursor.execute("SELECT id FROM organizations WHERE name = 'TenderMatch Evaluation Org' LIMIT 1")
    org_row = pg_cursor.fetchone()
    if org_row:
        eval_org_id = str(org_row[0])
    else:
        eval_org_id = str(uuid.uuid4())
        pg_cursor.execute("INSERT INTO organizations (id, name, type) VALUES (%s, %s, %s)", (eval_org_id, 'TenderMatch Evaluation Org', 'BUYER'))
    
    # Load model for embeddings
    print("Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    with open(os.path.join(data_dir, "tenders_50.json"), "r") as f:
        t_data = json.load(f)
        
    tenders = t_data["tenders"]
    ingested = []
    
    print(f"Ingesting {len(tenders)} tenders...")
    for t in tenders:
        # Insert to Mongo
        mongo_doc = {
            "title": t["title"],
            "type": "tender",
            "original_filename": f"{t['tender_id']}.pdf",
            "content": t["scope_of_work"], # Use scope as content
            "structured_data": {
                "sector": t["sector"],
                "issuing_authority": t["issuing_authority"],
                "location": t["location"],
                "district": t["district"],
                "scope_of_work": t["scope_of_work"],
                "min_turnover": t["min_turnover"],
                "min_experience_years": t["min_experience_years"],
                "estimated_value": t["estimated_value"],
                "mandatory_certifications": t["mandatory_certifications"],
                "submission_deadline": t["submission_deadline"],
                "duration_months": t["duration_months"],
            },
            "status": "completed",
            "created_at": datetime.now(timezone.utc)
        }
        res = mongo_db.documents.insert_one(mongo_doc)
        mongo_id = str(res.inserted_id)
        
        # Insert to Postgres
        tender_uuid = str(uuid.uuid4())
        summary_text = t["scope_of_work"][:500]
        summary_json = json.dumps({"text": summary_text})
        embedding = model.encode(summary_text).tolist()
        
        pg_cursor.execute("""
            INSERT INTO tenders (id, mongo_id, org_id, filename, scope, location, embedding, summary, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (tender_uuid, mongo_id, eval_org_id, f"{t['tender_id']}.pdf", t["scope_of_work"], t["location"], embedding, summary_json))
        
        ingested.append({
            "tender_id": t["tender_id"],
            "doc_id": tender_uuid,
            "mongo_id": mongo_id,
            "status": "completed"
        })
        
    pg_conn.commit()
    print("Tenders ingested.")
    
    # Read existing vendors from manifest since they succeeded
    manifest_path = os.path.join(data_dir, "ingestion_manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
            vendors = manifest.get("vendor_profiles", [])
    else:
        vendors = []
        
    manifest = {
        "evaluation_org_id": eval_org_id,
        "evaluation_user_id": "eval@tendermatch-research.internal",
        "access_token": "mocked",
        "tenders": ingested,
        "vendor_profiles": vendors,
        "ingested_at": datetime.now(timezone.utc).isoformat()
    }
    
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)
        
    print(f"Manifest updated with {len(ingested)} tenders and {len(vendors)} vendors.")

if __name__ == "__main__":
    direct_ingest()
