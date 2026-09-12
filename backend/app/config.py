from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

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

    cloud_database_url: str | None = Field(
        default=None,
        alias="CLOUD_DATABASE_URL"
    )
    tuya_cloud_time_offset_seconds: float = Field(
        default=0.0,
        alias="TUYA_CLOUD_TIME_OFFSET_SECONDS"
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

    @property
    def async_cloud_database_url(self) -> str | None:
        import os
        url = os.getenv("CLOUD_DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL") or self.cloud_database_url
        if not url:
            return None
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

settings = Settings()

