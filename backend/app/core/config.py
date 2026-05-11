from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Evaluación Docente IA"
    DATABASE_URL: Optional[str] = None
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    SECRET_KEY: str = "your-secret-key-change-it"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 1 week

    class Config:
        env_file = ".env"

settings = Settings()
