from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "AgentID"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "info"

    # Database
    database_url: str = "sqlite+aiosqlite:///./agentid.db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Security
    secret_key: str = "change-me-in-production-minimum-32-chars"
    private_key_path: Path = Path("keys/private_key.pem")
    public_key_path: Path = Path("keys/public_key.pem")

    # JWT defaults
    jwt_algorithm: str = "RS256"
    default_token_ttl_minutes: int = 15
    max_token_ttl_minutes: int = 1440  # 24h

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # Telemetry
    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url


settings = Settings()
