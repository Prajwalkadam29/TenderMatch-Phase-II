from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import connect_to_mongo, close_mongo_connection
from app.api import auth, organizations, users, upload, match, vendor_profiles, structured_match
from app.services.embedding_service import get_embedding_service


from fastapi_limiter import FastAPILimiter
from app.core.redis_client import init_redis, close_redis, get_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown lifecycle."""
    await connect_to_mongo()
    await init_redis()
    
    # Initialize rate limiter using Redis
    redis = get_redis()
    await FastAPILimiter.init(redis)
    
    # Pre-load embedding model + restore FAISS index from disk
    await get_embedding_service().warmup()
    yield
    await close_redis()
    await close_mongo_connection()


app = FastAPI(
    title="TenderMatch API",
    description="Phase 1+2 — Auth, Organizations, Document Parsing & Semantic Embeddings",
    version="2.0.0",
    lifespan=lifespan,
)

# ─── CORS & Logging Middleware ────────────────────────────────────────────────
from app.core.config import settings
from app.core.logging_config import setup_logging, request_id_ctx_var
import time
import logging
from uuid import uuid4
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware

setup_logging()
logger = logging.getLogger("http.access")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", uuid4().hex)
        token = request_id_ctx_var.set(req_id)
        start_time = time.perf_counter()
        
        logger.info(f"Incoming request: {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            process_time = time.perf_counter() - start_time
            logger.info(f"Completed request: {request.method} {request.url.path} with status {response.status_code} in {process_time:.4f}s")
            return response
        finally:
            request_id_ctx_var.reset(token)

app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import notify

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(upload.router)
app.include_router(match.router)
app.include_router(vendor_profiles.router)
app.include_router(structured_match.router)
app.include_router(notify.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "TenderMatch API is running"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
