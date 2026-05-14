from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    MONGODB_URI: str = "mongodb://localhost:27018"
    DATABASE_NAME: str = "tendermatch"

    # ── JWT Auth ──────────────────────────────────────────────────────────────
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    # Short access token (15 min production, longer for dev convenience)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    # Refresh token stored in httpOnly cookie
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
    ]

    # ── LLM ───────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6380/0"

    # ── SMTP / Email Notifications ────────────────────────────────────────────
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "no-reply@tendermatch.com"

    # ── Frontend URL (used in email links) ────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"

    # ── File uploads ──────────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"

    # ── Phase 2: PostgreSQL (Primary Relational Store) ────────────────────────────
    POSTGRES_URI: str = "postgresql+asyncpg://tendermatch:changeme@localhost:5433/tendermatch"
    POSTGRES_DB: str = "tendermatch"
    POSTGRES_USER: str = "tendermatch"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 20

    # ── Environment ───────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

