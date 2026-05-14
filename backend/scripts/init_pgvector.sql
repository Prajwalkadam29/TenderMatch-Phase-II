-- ─────────────────────────────────────────────────────────────────────────────
-- TenderMatch — PostgreSQL Initialization Script
-- This script runs ONCE on the first container start.
-- It enables the pgvector extension and sets up performance-critical settings.
-- ─────────────────────────────────────────────────────────────────────────────

-- Enable pgvector (pre-installed in pgvector/pgvector:pg16 image)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable trigram matching for keyword search (used by hybrid search in Phase 3)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable full-text search dictionary (used by tsvector hybrid search in Phase 3)
CREATE EXTENSION IF NOT EXISTS unaccent;
