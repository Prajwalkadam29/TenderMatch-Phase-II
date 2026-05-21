import asyncio
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy import text
from app.core.postgres import init_postgres, close_postgres, get_pg_session

async def main():
    await init_postgres()
    async with get_pg_session() as session:
        result = await session.execute(text("SELECT vendor_id, business_name, profile_completeness_pct, completeness_details FROM vendor_profiles WHERE org_id = '6806e04d-30af-4f53-bcb5-6ea4de2defbc' LIMIT 2"))
        vendors = result.fetchall()
        for v in vendors:
            print('ID:', v[0], 'Name:', v[1], 'Completeness:', v[2])
            print('Details:', json.dumps(v[3], indent=2))
            
    await close_postgres()

if __name__ == "__main__":
    asyncio.run(main())
