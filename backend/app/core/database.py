from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client: AsyncIOMotorClient = None
db = None

async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]
    # Existing indexes
    await db.users.create_index("email", unique=True)
    await db.organizations.create_index("name")
    # New: documents collection index
    await db.documents.create_index("type")
    await db.documents.create_index("created_at")
    # Vendor profiles indexes
    await db.vendor_profiles.create_index("user_id")
    await db.vendor_profiles.create_index("org_id")
    await db.vendor_profiles.create_index("vendor_id", unique=True, sparse=True)
    await db.vendor_profiles.create_index("is_active")
    print(f"[OK] Connected to MongoDB: {settings.DATABASE_NAME}")

async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("[INFO] MongoDB connection closed")

def get_db():
    return db
