import asyncio
import os
import sys
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.postgres import init_postgres, close_postgres, get_pg_session

async def main():
    await init_postgres()
    async with get_pg_session() as session:
        result = await session.execute(text("""
            SELECT v.vendor_id, w.weight_semantic, w.weight_financial, w.weight_experience, w.weight_certification
            FROM vendor_profile_weights w
            JOIN vendor_profiles v ON w.vendor_profile_id = v.id
            WHERE v.vendor_id IN ('V-EVAL-001', 'V-EVAL-004')
        """))
        rows = result.fetchall()
        for r in rows:
            print(f"{r[0]}: Semantic={r[1]}, Financial={r[2]}, Exp={r[3]}, Certs={r[4]}")
            
    await close_postgres()

if __name__ == "__main__":
    asyncio.run(main())
