"""
Configuration management using Pydantic Settings.
Validates all required environment variables at startup.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MongoDB Configuration
    mongodb_uri: str = Field(
        ...,
        description="MongoDB connection URI",
        json_schema_extra={"env": "MONGODB_URI"},
    )
    mongodb_db: str = Field(
        ...,
        description="MongoDB database name",
        json_schema_extra={"env": "MONGODB_DB"},
    )

    # MongoDB Connection Pool Settings
    mongo_max_pool_size: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of connections in the pool",
    )
    mongo_min_pool_size: int = Field(
        default=5, ge=0, le=50, description="Minimum number of connections in the pool"
    )
    mongo_max_idle_time_ms: int = Field(
        default=30000,
        ge=1000,
        description="Maximum time a connection can remain idle (ms)",
    )
    mongo_server_selection_timeout_ms: int = Field(
        default=5000, ge=1000, description="Server selection timeout (ms)"
    )

    # Bot API Token
    bot_api_token: str = Field(
        ...,
        min_length=16,
        description="Token for bot-to-API authentication",
        json_schema_extra={"env": "BOT_API_TOKEN"},
    )

    # JWT Configuration
    jwt_secret: str = Field(
        ...,
        min_length=32,
        description="Secret key for JWT signing",
        json_schema_extra={"env": "JWT_SECRET"},
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_expire_hours: int = Field(
        default=24, ge=1, description="JWT token expiration time in hours"
    )

    # Discord OAuth Configuration
    discord_client_id: str = Field(
        ...,
        description="Discord OAuth client ID",
        json_schema_extra={"env": "DISCORD_CLIENT_ID"},
    )
    discord_client_secret: str = Field(
        ...,
        description="Discord OAuth client secret",
        json_schema_extra={"env": "DISCORD_CLIENT_SECRET"},
    )
    discord_redirect_uri: str = Field(
        ...,
        description="Discord OAuth redirect URI",
        json_schema_extra={"env": "DISCORD_REDIRECT_URI"},
    )

    # Rate Limiting Configuration
    rate_limit: int = Field(
        default=60, ge=1, description="Number of requests allowed per period"
    )
    rate_period: int = Field(
        default=60, ge=1, description="Rate limit period in seconds"
    )

    # Redis Configuration (optional, falls back to in-memory if not set)
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL for distributed rate limiting",
        json_schema_extra={"env": "REDIS_URL"},
    )

    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        # Validate it's a proper comma-separated list
        origins = [o.strip() for o in v.split(",") if o.strip()]
        if not origins:
            raise ValueError("At least one CORS origin must be specified")
        return v

    def get_cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Settings are loaded once and cached for performance.
    Raises ValidationError at startup if required env vars are missing.
    """
    return Settings()


# Validate settings on module import (fail fast)
try:
    settings = get_settings()
except Exception as e:
    import sys

    print(f"Configuration Error: {e}", file=sys.stderr)
    print("\nRequired environment variables:", file=sys.stderr)
    print("  - MONGODB_URI: MongoDB connection string", file=sys.stderr)
    print("  - MONGODB_DB: Database name", file=sys.stderr)
    print(
        "  - BOT_API_TOKEN: API token for bot authentication (min 16 chars)",
        file=sys.stderr,
    )
    print("  - JWT_SECRET: Secret for JWT signing (min 32 chars)", file=sys.stderr)
    print("  - DISCORD_CLIENT_ID: Discord OAuth client ID", file=sys.stderr)
    print("  - DISCORD_CLIENT_SECRET: Discord OAuth client secret", file=sys.stderr)
    print("  - DISCORD_REDIRECT_URI: Discord OAuth redirect URI", file=sys.stderr)
    print("\nOptional environment variables:", file=sys.stderr)
    print("  - REDIS_URL: Redis URL for distributed rate limiting", file=sys.stderr)
    print("  - RATE_LIMIT: Requests per period (default: 60)", file=sys.stderr)
    print(
        "  - RATE_PERIOD: Rate limit period in seconds (default: 60)", file=sys.stderr
    )
    print("  - CORS_ORIGINS: Comma-separated allowed origins", file=sys.stderr)
    raise
