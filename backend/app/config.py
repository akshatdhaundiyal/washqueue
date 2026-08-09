from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Default to local postgresql if not specified
    database_url: str = Field(
        default="sqlite+aiosqlite:///./washqueue.db",
        alias="DATABASE_URL"
    )
    admin_pin: str = Field(
        default="1234",
        alias="ADMIN_PIN"
    )
    telemetry_poll_interval: int = Field(
        default=10,
        alias="TELEMETRY_POLL_INTERVAL"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        # Supabase and other providers use postgres:// or postgresql://.
        # SQLAlchemy asyncpg driver requires postgresql+asyncpg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

settings = Settings()

