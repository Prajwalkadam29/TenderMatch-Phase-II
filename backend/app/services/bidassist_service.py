import os
import logging
import httpx
from datetime import datetime, timezone
from sqlalchemy import select

from app.core.database import db, settings
from app.core.postgres import get_pg_session
from app.db.models.document import Tender
from app.tasks.ingestion_tasks import ingest_tender_document
from app.tasks.document_tasks import _save_tender_vector
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

class BidassistService:
    BASE_URL = os.getenv("BIDASSIST_API_URL", "https://api.example-bidassist.com")
    API_KEY = os.getenv("BIDASSIST_API_KEY", "dummy-key")
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Accept": "application/json"
        }
    
    async def fetch_tenders(self, category: str = None, state: str = None) -> list[dict]:
        # Mocking the actual fetch for this demo to avoid external API dependencies
        # In production:
        # async with httpx.AsyncClient() as client:
        #     res = await client.get(f"{self.BASE_URL}/tenders", params=..., headers=self.headers)
        #     return res.json().get("data", [])
        
        return [
            {
                "tender_id": "BA-1001",
                "title": "Supply of IT Equipment",
                "domain": "Information Technology",
                "scope_summary": "Supply of 500 laptops and accessories for government schools",
                "estimated_value": 25000000,
                "location_state": "Maharashtra",
                "min_avg_turnover": 50000000,
                "mandatory_certifications": ["ISO 9001", "ISO 27001"],
                "deadline": "2026-12-31T00:00:00Z",
                "extraction_confidence": 1.0,
                "pdf_url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
            },
            {
                "tender_id": "BA-1002",
                "title": "Road Construction NH-44",
                "domain": "Construction",
                "scope_summary": "Construction of 10km road in NH-44",
                "estimated_value": 150000000,
                "location_state": "Karnataka",
                "min_avg_turnover": 300000000,
                "mandatory_certifications": ["Class A Contractor"],
                "deadline": "2026-11-15T00:00:00Z",
                "extraction_confidence": 1.0,
                "pdf_url": None  # No PDF, persist directly
            }
        ]

    async def _download_pdf(self, url: str, filename: str) -> str:
        upload_dir = os.path.join(settings.UPLOAD_DIR, "tender")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            with open(file_path, "wb") as f:
                f.write(response.content)
        return file_path

    async def sync_tenders(self, category: str = None, state: str = None) -> dict:
        tenders = await self.fetch_tenders(category, state)
        
        stats = {
            "new_tenders": 0,
            "duplicates_skipped": 0,
            "errors": 0,
            "tender_ids": []
        }
        
        for t in tenders:
            try:
                tender_id = t["tender_id"]
                
                # Deduplication check: by tender_id OR (title + deadline + estimated_value)
                duplicate_query = {
                    "$or": [
                        {"metadata.reference_no": tender_id},
                        {"structured_data.tender_id": tender_id},
                        {
                            "original_filename": t["title"],
                            "structured_data.deadline": t["deadline"],
                            "structured_data.estimated_value": t["estimated_value"]
                        }
                    ]
                }
                
                existing = await db.documents.find_one(duplicate_query)
                if existing:
                    logger.info(f"[Bidassist] Duplicate skipped: {tender_id}")
                    stats["duplicates_skipped"] += 1
                    continue
                    
                # If PDF available, use standard pipeline
                if t.get("pdf_url"):
                    filename = f"{tender_id}.pdf"
                    file_path = await self._download_pdf(t["pdf_url"], filename)
                    
                    mongo_doc = {
                        "type": "tender",
                        "original_filename": filename,
                        "uploaded_by": "BIDASSIST_SYNC",
                        "org_id": None, # Global
                        "status": "processing",
                        "task_id": None,
                        "structured_data": {},
                        "keywords": [],
                        "search_text": "",
                        "raw_text": "",
                        "file_url": file_path,
                        "created_at": datetime.now(timezone.utc),
                        "metadata": {
                            "reference_no": tender_id,
                            "source": "bidassist_api"
                        }
                    }
                    result = await db.documents.insert_one(mongo_doc)
                    inserted_id = result.inserted_id
                    
                    await db.documents.update_one(
                        {"_id": inserted_id},
                        {"$set": {"mongo_id": str(inserted_id)}}
                    )
                    
                    # Dispatch to Celery
                    ingest_tender_document.delay(str(inserted_id), file_path, None, "BIDASSIST_SYNC")
                    
                    stats["new_tenders"] += 1
                    stats["tender_ids"].append(tender_id)
                    logger.info(f"[Bidassist] Queued PDF ingestion for {tender_id}")
                    
                else:
                    # Directly persist without LLM extraction
                    normalized_data = {
                        "tender_id": tender_id,
                        "source_portal": "bidassist_api",
                        "domain": t["domain"],
                        "scope_summary": t["scope_summary"],
                        "estimated_value": t["estimated_value"],
                        "location_state": t["location_state"],
                        "min_avg_turnover": t["min_avg_turnover"],
                        "mandatory_certifications": t["mandatory_certifications"],
                        "deadline": t["deadline"],
                        "extraction_confidence": t["extraction_confidence"]
                    }
                    
                    search_text = f"{t['title']} {t['scope_summary']} {t['location_state']} {t['domain']}"
                    
                    mongo_doc = {
                        "type": "tender",
                        "original_filename": t["title"],
                        "uploaded_by": "BIDASSIST_SYNC",
                        "org_id": None,
                        "status": "completed",
                        "task_id": None,
                        "structured_data": normalized_data,
                        "keywords": t["mandatory_certifications"],
                        "search_text": search_text,
                        "raw_text": "", # No raw text
                        "created_at": datetime.now(timezone.utc),
                        "is_global": True,
                        "metadata": {
                            "reference_no": tender_id,
                            "source": "bidassist_api"
                        }
                    }
                    
                    result = await db.documents.insert_one(mongo_doc)
                    inserted_id = result.inserted_id
                    
                    await db.documents.update_one(
                        {"_id": inserted_id},
                        {"$set": {"mongo_id": str(inserted_id)}}
                    )
                    
                    # Generate embedding
                    emb_service = get_embedding_service()
                    doc_vector = emb_service.encode_text_sync(search_text)
                    
                    # Save to PG
                    await _save_tender_vector(str(inserted_id), doc_vector, None)
                    
                    # Update summary in PG manually since we bypass ingestion task
                    async with get_pg_session() as session:
                        stmt = select(Tender).where(Tender.mongo_id == str(inserted_id))
                        pg_res = await session.execute(stmt)
                        pg_tender = pg_res.scalar_one_or_none()
                        if pg_tender:
                            pg_tender.summary = normalized_data
                            pg_tender.scope = t["scope_summary"]
                            pg_tender.location = t["location_state"]
                            pg_tender.filename = t["title"]
                            await session.commit()
                            
                    # Dispatch match
                    from app.tasks.matching_tasks import run_bulk_match_task
                    run_bulk_match_task.delay(tender_mongo_id=str(inserted_id), org_id=None)
                    
                    stats["new_tenders"] += 1
                    stats["tender_ids"].append(tender_id)
                    logger.info(f"[Bidassist] Persisted structured tender directly: {tender_id}")
                    
            except Exception as e:
                logger.error(f"[Bidassist] Error processing tender {t.get('tender_id')}: {e}")
                stats["errors"] += 1
                
        return stats
