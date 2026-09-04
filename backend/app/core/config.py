from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'app.db').as_posix()}"
    cors_origins: list[str] = ["http://localhost:5173"]
    environment: str = "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
