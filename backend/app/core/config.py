from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "tendermatch"
    JWT_SECRET: str = "tendermatch_secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Groq LLM
    GROQ_API_KEY: str = "secret-key"

    # File uploads – stored locally for PoC
    UPLOAD_DIR: str = "uploads"

    class Config:
        env_file = ".env"

settings = Settings()
