import os
import sys
import logging
from pymongo import MongoClient
from pymongo.errors import OperationFailure

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Try to load env vars manually if run directly
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass

def apply_schemas():
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("DATABASE_NAME", "tendermatch")
    
    client = MongoClient(mongo_uri)
    db = client[db_name]
    
    logger.info(f"Connected to MongoDB at {mongo_uri}")
    logger.info(f"Target Database: {db_name}")

    # 1. Schema for 'documents' collection (Tenders / unstructured vendor PDFs)
    documents_schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["type"],
            "properties": {
                "type": {
                    "enum": ["vendor", "tender"],
                    "description": "must be either vendor or tender and is required"
                },
                "filename": {
                    "bsonType": "string",
                    "description": "must be a string"
                },
                "embedding_id": {
                    "bsonType": ["int", "null"],
                    "description": "FAISS index pointer, must be int or null"
                },
                "created_at": {
                    "bsonType": "date",
                    "description": "creation timestamp"
                }
            }
        }
    }

    # 2. Schema for 'vendor_profiles' collection (Strict Pydantic-backed profiles)
    vendor_profiles_schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["org_id", "user_id", "is_active", "identity", "geography"],
            "properties": {
                "org_id": {
                    "bsonType": "string",
                    "description": "organization ID is required"
                },
                "user_id": {
                    "bsonType": "string",
                    "description": "user ID is required"
                },
                "is_active": {
                    "bsonType": "bool",
                    "description": "active status boolean is required"
                },
                "identity": {
                    "bsonType": "object",
                    "required": ["company_legal_name"],
                    "properties": {
                        "company_legal_name": {
                            "bsonType": "string"
                        }
                    }
                },
                "geography": {
                    "bsonType": "object",
                    "required": ["registered_states"],
                    "properties": {
                        "registered_states": {
                            "bsonType": "array",
                            "items": { "bsonType": "string" }
                        }
                    }
                }
            }
        }
    }

    collections_to_validate = {
        "documents": documents_schema,
        "vendor_profiles": vendor_profiles_schema
    }

    existing_collections = db.list_collection_names()

    for coll_name, schema in collections_to_validate.items():
        if coll_name not in existing_collections:
            logger.info(f"Collection '{coll_name}' does not exist. Creating with schema...")
            db.create_collection(coll_name, validator=schema)
            logger.info(f"✅ Created '{coll_name}' with schema validation.")
        else:
            logger.info(f"Collection '{coll_name}' exists. Applying schema validation via collMod...")
            try:
                db.command("collMod", coll_name, validator=schema, validationLevel="moderate", validationAction="error")
                logger.info(f"✅ Applied schema validation to existing '{coll_name}'.")
            except OperationFailure as e:
                logger.error(f"❌ Failed to apply schema to '{coll_name}': {e.details}")

    client.close()
    logger.info("MongoDB schema validation applied successfully.")

if __name__ == "__main__":
    apply_schemas()
