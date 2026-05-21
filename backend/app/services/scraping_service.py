import os
import json
import logging
import asyncio
import httpx
from datetime import datetime, timezone
from bs4 import BeautifulSoup

from app.core.database import db, settings
from app.tasks.ingestion_tasks import ingest_tender_document

logger = logging.getLogger(__name__)

class ScrapingService:
    def __init__(self):
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
        self.config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core",
            "portal_configs.json"
        )
        self.portals = self._load_configs()

    def _load_configs(self) -> list[dict]:
        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
                return [p for p in data.get("portals", []) if p.get("enabled", False)]
        except Exception as e:
            logger.error(f"Failed to load portal configs: {e}")
            return []

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

    async def _scrape_with_firecrawl(self, url: str) -> str:
        if not self.firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY not set")
            
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {self.firecrawl_api_key}",
                    "Content-Type": "application/json"
                },
                json={"url": url, "formats": ["html"]}
            )
            res.raise_for_status()
            data = res.json()
            return data.get("data", {}).get("html", "")

    async def _scrape_with_bs4_fallback(self, url: str) -> str:
        async with httpx.AsyncClient() as client:
            # Simple fallback using httpx
            res = await client.get(url, follow_redirects=True)
            res.raise_for_status()
            return res.text

    def _extract_tenders_from_html(self, html: str, config: dict) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        
        # Check for captchas or login walls
        if "captcha" in html.lower() or "verify you are human" in html.lower():
            logger.warning(f"[Scraper] Captcha detected on {config['name']}")
            return []
            
        if config.get("requires_login") or "login to continue" in html.lower():
            logger.warning(f"[Scraper] Login wall detected on {config['name']}")
            return []

        # Mock extraction logic
        # Real logic would use config['tender_link_selector']
        # This provides a dummy tender for testing the pipeline flow
        tenders = []
        
        # Generate dynamic dummy tender based on portal config
        tenders.append({
            "title": f"Infrastructure Development at {config['name']}",
            "reference_no": f"REF-{config['name'].upper().replace('.', '-')}-001",
            "deadline": "2026-12-31T00:00:00Z",
            "estimated_value": 7500000,
            "pdf_url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        })
        
        return tenders

    async def scrape_portal(self, config: dict) -> dict:
        stats = {"new_tenders": 0, "duplicates_skipped": 0, "errors": 0}
        url = config["scrape_url"]
        
        logger.info(f"[Scraper] Starting scrape for {config['name']} at {url}")
        
        try:
            # 1. Try Firecrawl API
            try:
                html = await self._scrape_with_firecrawl(url)
            except Exception as e:
                logger.warning(f"[Scraper] Firecrawl failed for {config['name']}: {e}. Falling back to bs4.")
                # 2. Fallback to basic httpx + bs4
                html = await self._scrape_with_bs4_fallback(url)
                
            tenders = self._extract_tenders_from_html(html, config)
            
            for t in tenders:
                ref_no = t["reference_no"]
                
                # Deduplication check
                duplicate_query = {
                    "$or": [
                        {"metadata.reference_no": ref_no},
                        {"structured_data.tender_id": ref_no},
                        {
                            "original_filename": t["title"],
                            "structured_data.deadline": t.get("deadline")
                        }
                    ]
                }
                
                existing = await db.documents.find_one(duplicate_query)
                if existing:
                    logger.info(f"[Scraper] Duplicate skipped: {ref_no}")
                    stats["duplicates_skipped"] += 1
                    continue
                    
                if t.get("pdf_url"):
                    filename = f"{ref_no}.pdf"
                    file_path = await self._download_pdf(t["pdf_url"], filename)
                    
                    mongo_doc = {
                        "type": "tender",
                        "original_filename": filename,
                        "uploaded_by": "WEB_SCRAPER",
                        "org_id": None,
                        "status": "processing",
                        "task_id": None,
                        "structured_data": {},
                        "keywords": [],
                        "search_text": "",
                        "raw_text": "",
                        "file_url": file_path,
                        "created_at": datetime.now(timezone.utc),
                        "metadata": {
                            "reference_no": ref_no,
                            "source": "web_scrape",
                            "portal": config["name"]
                        }
                    }
                    result = await db.documents.insert_one(mongo_doc)
                    inserted_id = result.inserted_id
                    
                    await db.documents.update_one(
                        {"_id": inserted_id},
                        {"$set": {"mongo_id": str(inserted_id)}}
                    )
                    
                    # Queue for standard ingestion pipeline
                    ingest_tender_document.delay(str(inserted_id), file_path, None, "WEB_SCRAPER")
                    
                    stats["new_tenders"] += 1
                    logger.info(f"[Scraper] Queued PDF ingestion for {ref_no}")
                    
                # Respect rate limits
                await asyncio.sleep(config.get("rate_limit_seconds", 2))
                
        except Exception as e:
            logger.error(f"[Scraper] Error scraping portal {config['name']}: {e}")
            stats["errors"] += 1
            
        return stats

    async def scrape_all_portals(self) -> dict:
        total_stats = {"new_tenders": 0, "duplicates_skipped": 0, "errors": 0, "portals_scraped": 0}
        
        for config in self.portals:
            stats = await self.scrape_portal(config)
            total_stats["new_tenders"] += stats["new_tenders"]
            total_stats["duplicates_skipped"] += stats["duplicates_skipped"]
            total_stats["errors"] += stats["errors"]
            total_stats["portals_scraped"] += 1
            
        return total_stats
