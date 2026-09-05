from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'app.db').as_posix()}"
    cors_origins: list[str] = ["http://localhost:5173"]
    environment: str = "local"

    # Auth / sessions
    session_cookie_name: str = "session"
    csrf_cookie_name: str = "csrf"
    session_ttl_hours: int = 24 * 14
    invitation_ttl_hours: int = 24 * 7
    password_reset_ttl_hours: int = 2
    login_rate_limit_attempts: int = 10
    login_rate_limit_window_seconds: int = 60

    # Local development only — never used to seed a production database.
    dev_seed_password: str = "DevPassword123!"

    @property
    def cookie_secure(self) -> bool:
        return self.environment != "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
