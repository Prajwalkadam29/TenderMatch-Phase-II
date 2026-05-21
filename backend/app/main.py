from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.database import connect_to_mongo, close_mongo_connection, get_db
from app.core.postgres import init_postgres, close_postgres
from app.api import auth, organizations, users, upload, match, vendor_profiles, structured_match, activity
from app.services.embedding_service import get_embedding_service
from fastapi_limiter import FastAPILimiter
from app.core.redis_client import init_redis, close_redis, get_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown lifecycle."""
    await connect_to_mongo()
    await init_redis()
    await init_postgres()

    # Initialize rate limiter using Redis
    redis = get_redis()
    await FastAPILimiter.init(redis)

    # Load embedding model in background so app becomes healthy faster
    import asyncio
    asyncio.create_task(get_embedding_service().warmup())
    yield
    await close_postgres()
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
app.include_router(activity.router)
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(upload.router)
app.include_router(match.router)
app.include_router(vendor_profiles.router)
app.include_router(structured_match.router)
app.include_router(notify.router)
from app.api import tenders
app.include_router(tenders.router)
from app.api import scrapers, admin
app.include_router(scrapers.router)
app.include_router(admin.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "TenderMatch API is running"}


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Deep health check: verifies connectivity to MongoDB and Redis.
    Returns 503 if any dependency is degraded.
    Used by Docker healthcheck, load balancers, and uptime monitors.
    """
    import time

    services = {}
    healthy = True

    # ── MongoDB ──────────────────────────────────────────────────────────────
    try:
        db = get_db()
        t0 = time.perf_counter()
        await db.command("ping")
        services["mongodb"] = {"status": "ok", "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
    except Exception as exc:
        services["mongodb"] = {"status": "error", "detail": str(exc)}
        healthy = False

    # ── Redis ───────────────────────────────────────────────────────────────
    try:
        redis = get_redis()
        if redis:
            t0 = time.perf_counter()
            await redis.ping()
            services["redis"] = {"status": "ok", "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
        else:
            services["redis"] = {"status": "not_initialized"}
            healthy = False
    except Exception as exc:
        services["redis"] = {"status": "error", "detail": str(exc)}
        healthy = False

    # ── PostgreSQL ──────────────────────────────────────────────────────────
    try:
        from app.core.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        async with engine.connect() as conn:
            t0 = time.perf_counter()
            await conn.execute(text("SELECT 1"))
            services["postgres"] = {"status": "ok", "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
    except Exception as exc:
        services["postgres"] = {"status": "error", "detail": str(exc)}
        healthy = False

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if healthy else "degraded",
            "services": services,
        },
    )
