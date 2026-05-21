import asyncio
from app.core.postgres import init_postgres, get_pg_session
from app.db.models.user import User
from app.db.models.organization import Organization
from sqlalchemy import select
import uuid

async def check_and_fix_user(email, password):
    await init_postgres()
    async with get_pg_session() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if not user:
            print(f"User {email} not found.")
            # I can't register via SQL easily because of password hashing, 
            # so I'll just report it.
            return False
        
        if not user.org_id:
            print(f"Fixing org_id for {email}...")
            org = await session.scalar(select(Organization).limit(1))
            if not org:
                org = Organization(name="General Org", is_active=True)
                session.add(org)
                await session.flush()
            user.org_id = org.id
            await session.commit()
            print(f"Assigned Org ID: {org.id}")
        else:
            print(f"User has Org ID: {user.org_id}")
        return True

if __name__ == "__main__":
    asyncio.run(check_and_fix_user("atharva@gmail.com", "user@1234"))
