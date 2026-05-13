import asyncio
import logging
from celery import shared_task
from datetime import datetime

from app.scrapers.tendertiger_scraper import TenderTigerScraper
from app.core.database import client, db, settings

logger = logging.getLogger(__name__)

# To run async code inside a synchronous Celery task
def run_async(coro):
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
    from pymongo import MongoClient
    
    # We must use a sync MongoClient inside a Celery worker thread
    sync_client = MongoClient(settings.MONGODB_URI)
    sync_db = sync_client[settings.DATABASE_NAME]

    for item in scraped_data:
        # Check if we already scraped this tender to prevent duplicates
        existing = sync_db.documents.find_one({"metadata.reference_no": item["reference_no"]})
        if existing:
            continue
            
        # Create a document schema for the scraped tender
        doc = {
            "filename": item["title"],
            "type": "tender",
            "search_text": f"{item['title']} {item['description']} {item['location']} {item['organization']}",
            "metadata": {
                "reference_no": item["reference_no"],
                "organization": item["organization"],
                "location": item["location"],
                "estimated_value": item["estimated_value"],
                "source": item["tender_url"]
            },
            "status": "completed", # For now, we skip raw PDF extraction and assume complete
            "uploaded_by": "SYSTEM_SCRAPER",
            "created_at": datetime.utcnow()
        }
        
        result = sync_db.documents.insert_one(doc)
        inserted_count += 1
        
        # In a full pipeline, we would now trigger:
        # 1. FAISS embedding generation for this new document
        # 2. Automated Matching engine against all vendor profiles
        # 3. Email notifications for high matches
        
    sync_client.close()
    
    logger.info(f"Automated scraper finished. Inserted {inserted_count} new tenders.")
    return f"Inserted {inserted_count} new tenders."
