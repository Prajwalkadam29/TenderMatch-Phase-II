from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import connect_to_mongo, close_mongo_connection
from app.api import auth, organizations, users, upload, match
from app.services.embedding_service import get_embedding_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown lifecycle."""
    await connect_to_mongo()
    # Pre-load embedding model + restore FAISS index from disk
    await get_embedding_service().warmup()
    yield
    await close_mongo_connection()


app = FastAPI(
    title="TenderMatch API",
    description="Phase 1+2 — Auth, Organizations, Document Parsing & Semantic Embeddings",
    version="2.0.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite default
        "http://localhost:5174",   # Vite alternate port
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(upload.router)
app.include_router(match.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "TenderMatch API is running"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
