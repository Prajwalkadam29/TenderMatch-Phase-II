import json
import asyncio
from app.core.database import get_db, connect_to_mongo

async def generate():
    await connect_to_mongo()
    db = get_db()
    
    tenders = await db.documents.find({'type': 'tender'}).to_list(100)
    from sqlalchemy import select
    from app.core.postgres import get_pg_session, init_postgres
    from app.db.models.document import VendorProfile
    
    await init_postgres()
    async with get_pg_session() as session:
        vendors = (await session.execute(select(VendorProfile))).scalars().all()

    manifest = {
        'tenders': [
            {
                'tender_id': t.get('original_filename', '').split('_')[-1].replace('.pdf', ''),
                'mongo_id': str(t['_id'])
            } for t in tenders
        ],
        'vendor_profiles': [
            {
                'vendor_id': getattr(v, 'vendor_id', ''),
                'profile_id': str(v.id)
            } for v in vendors
        ],
        'access_token': 'dummy'
    }
    
    with open('evaluation/data/ingestion_manifest.json', 'w') as f:
        json.dump(manifest, f, indent=4)
        
    print(f"Generated manifest with {len(tenders)} tenders and {len(vendors)} vendors.")

if __name__ == '__main__':
    asyncio.run(generate())
