import asyncio
import uuid
from app.services.matching_service import run_matching_engine
from app.core.postgres import get_pg_session, init_postgres
from app.db.models.document import VendorProfile
from sqlalchemy import select

async def check():
    from app.core.database import connect_to_mongo
    await connect_to_mongo()
    await init_postgres()
    async with get_pg_session() as session:
        result = await session.execute(select(VendorProfile).order_by(VendorProfile.created_at.desc()).limit(1))
        vp = result.scalar_one_or_none()
        if not vp:
            print('No profile')
            return
        
        print(f'Matching for {vp.business_name} ({vp.id})')
        results = await run_matching_engine(str(vp.id), top_k=10, explain=False)
        for res in results:
            print(f"{res['final_score']}% - {res['tender_title']}")

if __name__ == '__main__':
    asyncio.run(check())
