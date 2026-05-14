import asyncio
import logging
from celery import shared_task
from datetime import datetime

from app.scrapers.tendertiger_scraper import TenderTigerScraper
from app.core.database import client, db, settings
from app.core.celery_db import get_celery_db

logger = logging.getLogger(__name__)

# To run async code inside a synchronous Celery task cleanly
def run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)

@shared_task(name="run_automated_scraper")
def run_automated_scraper():
    """
    Celery Beat task to run web scrapers periodically, parse the data,
    and insert new tenders into MongoDB.
    """
    logger.info("Starting automated scraper pipeline...")
    
    scraper = TenderTigerScraper()
    scraped_data = run_async(scraper.fetch_latest_tenders(limit=5))
    
    if not scraped_data:
        logger.info("No new tenders scraped.")
        return "No data found."
        
    inserted_count = 0
    sync_db = get_celery_db()

    for item in scraped_data:
        ref_no = item["reference_no"]
        
        # High-speed Redis check to prevent DB load
        if not run_async(scraper.is_new_tender(ref_no)):
            continue

        # Database fallback check
        existing = sync_db.documents.find_one({"metadata.reference_no": ref_no})
        if existing:
            run_async(scraper.mark_as_scraped(ref_no))
            continue
            
        # Create a document schema for the scraped tender with normalized structured_data
        doc = {
            "filename": item["title"],
            "type": "tender",
            "search_text": f"{item['title']} {item['description']} {item['location']} {item['organization']}",
            "structured_data": {
                "scope": item["description"],
                "location": item["location"],
                "organization": item["organization"],
                "certifications": [], # Scraper can't easily extract this yet
                "eligibility": "Open to all qualified vendors"
            },
            "metadata": {
                "reference_no": ref_no,
                "organization": item["organization"],
                "location": item["location"],
                "estimated_value": item["estimated_value"],
                "source": item["tender_url"]
            },
            "status": "completed",
            "uploaded_by": "SYSTEM_SCRAPER",
            "created_at": datetime.utcnow()
        }
        
        result = sync_db.documents.insert_one(doc)
        inserted_id = result.inserted_id
        inserted_count += 1
        run_async(scraper.mark_as_scraped(ref_no))
        
        # 1. Trigger pgvector embedding generation for the new scraped document
        from app.services.embedding_service import get_embedding_service
        from app.tasks.document_tasks import _save_vector_to_postgres
        emb_svc = get_embedding_service()
        
        # We use the combined search_text for semantic indexing
        doc_vector = emb_svc.encode_text_sync(doc["search_text"])
        keywords = [item["organization"], item["location"]]
        
        _save_vector_to_postgres(
            doc_id_str=str(inserted_id),
            doc_type="tender",
            vector=doc_vector,
            keywords=keywords
        )
        
        logger.info(f"[Scraper] Indexed tender {ref_no} natively in PostgreSQL (pgvector).")
        
    logger.info(f"Automated scraper finished. Inserted {inserted_count} new tenders.")
    return f"Inserted {inserted_count} new tenders."
