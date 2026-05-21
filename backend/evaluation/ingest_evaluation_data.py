"""
Evaluation Data Ingestion Script
Ingests synthetic tenders and vendor profiles via the TenderMatch API.
Uses a dedicated evaluation organization to isolate test data from production.
"""
import os
import json
import time
import httpx
import asyncio
from datetime import datetime, timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

API_BASE = "http://localhost:8000"

def create_tender_pdf(tender: dict, filepath: str):
    """Generate a simple PDF from tender JSON data."""
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, f"Tender Document: {tender['title']}")
    
    c.setFont("Helvetica", 10)
    y = 720
    for key, value in tender.items():
        text = f"{key}: {value}"
        # Simple text wrapping for scope_of_work
        if len(text) > 80:
            words = text.split()
            line = ""
            for word in words:
                if len(line + word) > 80:
                    c.drawString(50, y, line)
                    y -= 15
                    line = word + " "
                else:
                    line += word + " "
            c.drawString(50, y, line)
            y -= 15
        else:
            c.drawString(50, y, text)
            y -= 15
            
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = 750
            
    c.save()

async def register_eval_user(client: httpx.AsyncClient):
    """Register evaluation organization and user."""
    payload = {
        "email": "eval3@tendermatch-research.internal",
        "name": "Evaluation User",
        "password": "EvalSecure2026!",
        "org_name": "TenderMatch Evaluation Org",
        "org_type": "BUYER",
        "role": "ADMIN1"
    }
    
    # Try logging in first in case it already exists
    login_data = {"email": payload["email"], "password": payload["password"]}
    try:
        login_resp = await client.post(f"{API_BASE}/auth/login", json=login_data)
        if login_resp.status_code == 200:
            print("User already exists. Logged in successfully.")
            return login_resp.json()["access_token"]
    except Exception:
        pass

    print("Registering new evaluation user...")
    resp = await client.post(f"{API_BASE}/auth/register", json=payload)
    if resp.status_code in (200, 201):
        login_resp = await client.post(f"{API_BASE}/auth/login", json=login_data)
        return login_resp.json()["access_token"]
    else:
        # If already registered, auth/register returns 400
        print(f"Registration response: {resp.status_code} {resp.text}")
        login_resp = await client.post(f"{API_BASE}/auth/login", json=login_data)
        if login_resp.status_code == 200:
            return login_resp.json()["access_token"]
        raise Exception("Failed to register and login evaluation user.")

async def ingest_tenders(client: httpx.AsyncClient, token: str, data_dir: str):
    tenders_path = os.path.join(data_dir, "tenders_50.json")
    with open(tenders_path, "r") as f:
        data = json.load(f)
        
    tenders = data
    ingested = []
    
    headers = {"Authorization": f"Bearer {token}"}
    
    for i, tender in enumerate(tenders):
        pdf_path = os.path.join(data_dir, f"temp_{tender['tender_id']}.pdf")
        create_tender_pdf(tender, pdf_path)
        
        print(f"[{i+1}/{len(tenders)}] Uploading tender {tender['tender_id']}...")
        
        with open(pdf_path, "rb") as f:
            files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
            # Also pass structured data as form fields to help the pipeline if needed
            data_payload = {"tender_id": tender["tender_id"]}
            resp = await client.post(
                f"{API_BASE}/upload/tender", 
                headers=headers, 
                files=files,
                data=data_payload
            )
            
        if resp.status_code not in (200, 201, 202):
            print(f"Failed to upload tender {tender['tender_id']}: {resp.status_code} {resp.text}")
            continue
            
        result = resp.json()
        doc_id = result.get("document_id") or result.get("id")
        
        # Poll for completion
        status = "processing"
        attempts = 0
        mongo_id = None
        while status not in ["completed", "failed", "processed"] and attempts < 180:
            await asyncio.sleep(2)
            try:
                stat_resp = await client.get(f"{API_BASE}/upload/documents/{doc_id}", headers=headers)
                if stat_resp.status_code == 200:
                    stat_data = stat_resp.json()
                    status = stat_data.get("status", "processing")
                    mongo_id = stat_data.get("mongo_id")
            except Exception:
                pass
            attempts += 1
            
        if status in ["completed", "processed"]:
            ingested.append({
                "tender_id": tender["tender_id"],
                "doc_id": doc_id,
                "mongo_id": mongo_id,
                "status": "completed"
            })
        else:
            print(f"Tender {tender['tender_id']} stuck in status {status}")
            
        # Clean up PDF
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            
    return ingested

async def ingest_vendors(client: httpx.AsyncClient, token: str, data_dir: str):
    vendors_path = os.path.join(data_dir, "vendors_10.json")
    with open(vendors_path, "r") as f:
        data = json.load(f)
        
    vendors = data["vendors"]
    ingested = []
    
    headers = {"Authorization": f"Bearer {token}"}
    
    for i, vendor in enumerate(vendors):
        print(f"[{i+1}/{len(vendors)}] Creating vendor profile {vendor['vendor_id']}...")
        
        resp = await client.post(
            f"{API_BASE}/vendor-profiles/", 
            headers=headers, 
            json=vendor["profile_data"]
        )
        
        if resp.status_code in (200, 201):
            result = resp.json()
            profile_id = result.get("id") or result.get("_id") or result.get("vendor_profile_id")
            ingested.append({
                "vendor_id": vendor["vendor_id"],
                "profile_id": str(profile_id),
                "business_name": vendor["business_name"]
            })
        else:
            print(f"Failed to create vendor {vendor['vendor_id']}: {resp.status_code} {resp.text}")
            
    return ingested

async def main():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            token = await register_eval_user(client)
        except Exception as e:
            print(f"Error during registration/login: {e}")
            return
            
        print("\nStarting Tender Ingestion...")
        ingested_tenders = await ingest_tenders(client, token, data_dir)
        
        print("\nStarting Vendor Ingestion...")
        ingested_vendors = await ingest_vendors(client, token, data_dir)
        
        # Save manifest
        manifest = {
            "evaluation_org_id": "TenderMatch Evaluation Org", # Can query real ID if needed
            "evaluation_user_id": "eval@tendermatch-research.internal",
            "access_token": token,
            "tenders": ingested_tenders,
            "vendor_profiles": ingested_vendors,
            "ingested_at": datetime.now(timezone.utc).isoformat()
        }
        
        manifest_path = os.path.join(data_dir, "ingestion_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=4)
            
        # Print summary
        print("\nIngestion Complete")
        print("==================")
        print(f"Tenders ingested: {len(ingested_tenders)}/50")
        print(f"Failed tenders: {50 - len(ingested_tenders)}")
        print(f"Vendor profiles created: {len(ingested_vendors)}/10")
        
        # Breakdown calculation
        with open(os.path.join(data_dir, "tenders_50.json"), "r") as f:
            t_data = json.load(f)
        
        domains = {}
        for t in t_data:
            domains[t["sector"]] = domains.get(t["sector"], 0) + 1
            
        print("\nDomain breakdown:")
        for dom, cnt in domains.items():
            print(f"  {dom}: {cnt} tenders")
            
        with open(os.path.join(data_dir, "vendors_10.json"), "r") as f:
            v_data = json.load(f)
            
        comps = {">= 85%": 0, "65-84%": 0, "< 65%": 0}
        for v in v_data["vendors"]:
            pct = v["profile_completeness_pct"]
            if pct >= 85: comps[">= 85%"] += 1
            elif pct >= 65: comps["65-84%"] += 1
            else: comps["< 65%"] += 1
            
        print("\nProfile completeness distribution:")
        for k, v in comps.items():
            print(f"  {k}: {v} profiles")
        
        print(f"\nManifest saved to: {manifest_path}")

if __name__ == "__main__":
    asyncio.run(main())
