import asyncio
import os
import sys
from sqlalchemy import text, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import get_db, connect_to_mongo, close_mongo_connection
from app.core.postgres import init_postgres, close_postgres, get_pg_session
from app.services.embedding_service import get_embedding_service
from app.db.models.document import VendorProfile

async def main():
    await init_postgres()
    await connect_to_mongo()
    db = get_db()
    
    emb_service = get_embedding_service()
    
    async with get_pg_session() as session:
        result = await session.execute(text("SELECT id FROM vendor_profiles WHERE vendor_id LIKE 'V-EVAL-%'"))
        vendor_ids = [row[0] for row in result.fetchall()]
        
        result = await session.execute(select(VendorProfile).where(VendorProfile.id.in_(vendor_ids)))
        vendors = result.scalars().all()
        
        for v in vendors:
            # Recreate text to embed
            name = v.business_name or v.profile_data.get("identity", {}).get("company_legal_name", "")
            desc = v.profile_data.get("business_domain", {}).get("capability_description_freetext", "")
            text_to_embed = f"{name} {desc}"
            
            vec = await emb_service.encode_text(text_to_embed)
            if vec:
                v.embedding = vec
                print(f"Generated embedding for {v.vendor_id}")
            else:
                print(f"Failed to generate embedding for {v.vendor_id}")
                
        await session.commit()
        print("Embeddings updated successfully.")
        
    await close_postgres()
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
