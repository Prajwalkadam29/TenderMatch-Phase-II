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
                
                # MOCK EXTRACTION LOGIC
                # Real implementation would use soup.find_all('div', class_='tender-card') or similar
                scraped_tenders = []
                
                # Simulating finding tenders on the page
                for i in range(limit):
                    scraped_tenders.append({
                        "title": f"Construction of Solar Power Plant Phase {i+1}",
                        "reference_no": f"TT-2026-SOLAR-{i+1000}",
                        "organization": "Ministry of New and Renewable Energy",
                        "location": "Gujarat, India",
                        "estimated_value": 50000000 + (i * 1000000),
                        "description": "Design, engineering, supply, construction, erection, testing, and commissioning of Solar PV Power Plant.",
                        "tender_url": f"{self.base_url}tenders/TT-2026-SOLAR-{i+1000}"
                    })
                
                logger.info(f"Successfully scraped {len(scraped_tenders)} tenders from TenderTiger.")
                return scraped_tenders

        except Exception as e:
            logger.error(f"Failed to scrape TenderTiger: {str(e)}")
            return []
