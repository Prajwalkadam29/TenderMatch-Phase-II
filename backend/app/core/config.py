from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb://localhost:27018"
    DATABASE_NAME: str = "tendermatch"
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Groq LLM
    GROQ_API_KEY: str

    # Redis configuration
    REDIS_URL: str = "redis://localhost:6380/0"

    # SMTP / Email Notifications
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "no-reply@tendermatch.com"

    # File uploads – stored locally for PoC
    UPLOAD_DIR: str = "uploads"

    class Config:
        env_file = ".env"

settings = Settings()
