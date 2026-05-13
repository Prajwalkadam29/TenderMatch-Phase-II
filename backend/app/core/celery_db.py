import logging
from pymongo import MongoClient
from celery.signals import worker_process_init, worker_process_shutdown
from app.core.config import settings

logger = logging.getLogger(__name__)

mongo_client: MongoClient = None
mongo_db = None

@worker_process_init.connect
def init_worker_mongo(**kwargs):
    global mongo_client, mongo_db
    logger.info("[Celery Worker] Initializing MongoDB connection pool...")
    mongo_client = MongoClient(settings.MONGODB_URI, maxPoolSize=50)
    mongo_db = mongo_client[settings.DATABASE_NAME]
    logger.info("[Celery Worker] MongoDB connection pool initialized.")

@worker_process_shutdown.connect
def shutdown_worker_mongo(**kwargs):
    global mongo_client
    if mongo_client:
        logger.info("[Celery Worker] Closing MongoDB connection pool...")
        mongo_client.close()
        logger.info("[Celery Worker] MongoDB connection pool closed.")

def get_celery_db():
    global mongo_db
    if mongo_db is None:
        client = MongoClient(settings.MONGODB_URI, maxPoolSize=50)
        return client[settings.DATABASE_NAME]
    return mongo_db
