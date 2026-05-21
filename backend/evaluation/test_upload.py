import asyncio
import httpx
import os
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

API_BASE = "http://localhost:8000"

async def test():
    async with httpx.AsyncClient() as client:
        login_data = {"email": "eval@tendermatch-research.internal", "password": "EvalSecure2026!"}
        login_resp = await client.post(f"{API_BASE}/auth/login", json=login_data)
        token = login_resp.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        pdf_path = "test.pdf"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, "Test Tender Document")
        c.save()
        
        with open(pdf_path, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            resp = await client.post(
                f"{API_BASE}/upload/tender", 
                headers=headers, 
                files=files
            )
        print("Tender Upload:", resp.status_code, resp.text)
        
        if os.path.exists(pdf_path): os.remove(pdf_path)

        # Test Vendor Profile Upload
        vendor_payload = {
            "company_legal_name": "Test Company",
            "registration_type": "Pvt Ltd",
            "pan_number": "ABCDE1234F",
            "gstin": "27ABCDE1234F1Z5",
            "year_of_incorporation": 2012,
            "registered_state": "Maharashtra",
            "registered_city": "Mumbai",
            "operational_states": ["Maharashtra"],
            "primary_domains": ["Civil"],
            "sub_domains": ["Civil"],
            "capabilities_freetext": "Test",
            "average_annual_turnover_inr": 450_000_000,
            "turnover_by_year": [],
            "net_worth_inr": 150_000_000,
            "past_projects": [],
            "iso_certifications": [],
            "domain_licenses": [],
            "blacklisted": False,
            "msme_registered": False,
            "msme_category": None
        }
        resp = await client.post(f"{API_BASE}/vendor-profiles/", headers=headers, json=vendor_payload)
        print("Vendor Profile:", resp.status_code, resp.text)

asyncio.run(test())
