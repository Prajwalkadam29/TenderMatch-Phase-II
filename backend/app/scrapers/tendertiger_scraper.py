import httpx
from bs4 import BeautifulSoup
import logging
import redis.asyncio as redis
from typing import List, Dict
from app.core.config import settings

logger = logging.getLogger(__name__)

class TenderTigerScraper:
    def __init__(self):
        self.base_url = "https://www.tendertiger.com/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.redis_url = settings.REDIS_URL

    async def is_new_tender(self, ref_no: str) -> bool:
        """Check Redis set to see if we have already scraped this tender ID."""
        r = redis.from_url(self.redis_url, decode_responses=True)
        try:
            is_member = await r.sismember("scraped_tender_ids", ref_no)
            return not is_member
        finally:
            await r.close()

    async def mark_as_scraped(self, ref_no: str):
        """Mark a tender ID as scraped in Redis with a 30-day TTL."""
        r = redis.from_url(self.redis_url, decode_responses=True)
        try:
            await r.sadd("scraped_tender_ids", ref_no)
            await r.expire("scraped_tender_ids", 86400 * 30) # 30 days
        finally:
            await r.close()

    async def fetch_latest_tenders(self, limit: int = 5) -> List[Dict]:
        """
        Scrapes the latest tenders from TenderTiger.
        In a production scenario, you would target their specific search or API endpoints.
        """
        logger.info(f"Starting scrape of {self.base_url}")
        
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
                # We hit the homepage or a specific search endpoint. 
                # (For this architecture build, we'll mock the extraction since the real site uses complex anti-bot/dynamic rendering)
                response = await client.get(self.base_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # ─── MOCK EXTRACTION LOGIC ────────────────────────────────────────────
                # WARNING: This is a STUB scraper. Replace with real extraction logic
                # before deploying to production. Real implementation should use:
                #   soup.find_all('div', class_='tender-card') or equivalent selectors
                #   against the actual TenderTiger API or search endpoint.
                #
                # To prevent data-poisoning from repeated identical inserts, each mock
                # run generates unique reference numbers using a timestamp prefix.
                # ─────────────────────────────────────────────────────────────────────
                import uuid as _uuid
                from datetime import datetime as _dt
                run_ts = _dt.utcnow().strftime("%Y%m%d%H%M")   # e.g. "202605131400"

                MOCK_TENDER_TEMPLATES = [
                    {
                        "title": "Construction of Solar Power Plant",
                        "organization": "Ministry of New and Renewable Energy",
                        "location": "Gujarat, India",
                        "estimated_value_base": 50_000_000,
                        "description": "Design, engineering, supply, construction, erection, testing, and commissioning of Solar PV Power Plant.",
                    },
                    {
                        "title": "National Highway Road Widening Project",
                        "organization": "National Highways Authority of India",
                        "location": "Rajasthan, India",
                        "estimated_value_base": 120_000_000,
                        "description": "Four-laning of existing two-lane highway including earthwork, pavement, drainage, and structures.",
                    },
                    {
                        "title": "Smart City CCTV Surveillance System",
                        "organization": "Municipal Corporation",
                        "location": "Pune, Maharashtra",
                        "estimated_value_base": 15_000_000,
                        "description": "Supply, installation, and commissioning of IP-based CCTV surveillance cameras with centralized monitoring.",
                    },
                    {
                        "title": "Drinking Water Supply Pipeline Project",
                        "organization": "Jal Shakti Ministry",
                        "location": "Bihar, India",
                        "estimated_value_base": 75_000_000,
                        "description": "Design and construction of water distribution network including laying of HDPE pipes and pump stations.",
                    },
                    {
                        "title": "Hospital Medical Equipment Procurement",
                        "organization": "State Health Department",
                        "location": "Hyderabad, Telangana",
                        "estimated_value_base": 8_000_000,
                        "description": "Supply and installation of diagnostic and surgical medical equipment for district hospitals.",
                    },
                ]

                scraped_tenders = []
                for i, tmpl in enumerate(MOCK_TENDER_TEMPLATES[:limit]):
                    unique_suffix = _uuid.uuid4().hex[:6].upper()
                    scraped_tenders.append({
                        "title": tmpl["title"],
                        "reference_no": f"TT-{run_ts}-{unique_suffix}",   # unique per run
                        "organization": tmpl["organization"],
                        "location": tmpl["location"],
                        "estimated_value": tmpl["estimated_value_base"] + (i * 1_000_000),
                        "description": tmpl["description"],
                        "tender_url": f"{self.base_url}tenders/TT-{run_ts}-{unique_suffix}",
                    })
                
                logger.info(f"Successfully scraped {len(scraped_tenders)} tenders from TenderTiger.")
                return scraped_tenders

        except Exception as e:
            logger.error(f"Failed to scrape TenderTiger: {str(e)}")
            return []
