# ─── STAGE 1: Builder ────────────────────────────────────────────────────────
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN python -m venv /opt/venv

COPY requirements-ai.txt .
COPY requirements.txt .

# ── Step 1: Install Heavy AI Libraries (Cached permanently) ──────────────────
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-ai.txt

# ── Step 2: Install App Libraries (Fast rebuilds) ───────────────────────────
RUN pip install --no-cache-dir -r requirements.txt

# ─── STAGE 2: Production Slim Runner ─────────────────────────────────────────
FROM python:3.10-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

# Runtime dependencies only (no build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY . /app

RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
