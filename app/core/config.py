# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional, List
import os

default_db = os.getenv("DATABASE_URL")
if not default_db:
    if os.getenv("TEST_DATABASE", "sqlite").lower() == "postgres":
        default_db = "postgresql://postgres:postgres@localhost:5432/fastapi_db"
    else:
        default_db = "sqlite:///./test_db.sqlite"

class Settings(BaseSettings):
    DATABASE_URL: str = default_db
    
    JWT_SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    JWT_REFRESH_SECRET_KEY: str = "your-refresh-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    BCRYPT_ROUNDS: int = 12
    CORS_ORIGINS: List[str] = ["*"]
    
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

@lru_cache()
def get_settings() -> Settings:
    return Settings()