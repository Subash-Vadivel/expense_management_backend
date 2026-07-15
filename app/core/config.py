from __future__ import annotations

from functools import lru_cache
import ssl
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Farm Accounts API"
    environment: str = "development"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_dbname: str = "postgres"
    postgres_sslmode: str = "require"
    jwt_secret_key: str = Field(default="change-me", min_length=8)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        enable_decoding=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def async_database_url(self) -> str:
        password = quote_plus(self.postgres_password)
        url = (
            f"postgresql+asyncpg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_dbname}"
        )
        return url

    @property
    def postgres_connect_args(self) -> dict:
        sslmode = (self.postgres_sslmode or "").lower()
        if sslmode in {"disable", "false", "0", ""}:
            return {}
        if sslmode == "require":
            # Match libpq sslmode=require semantics: encrypt the connection without CA verification.
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return {"ssl": context}
        return {"ssl": True}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
