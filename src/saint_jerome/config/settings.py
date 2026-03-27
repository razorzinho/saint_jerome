from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    discord_token: str = Field(default="")
    default_translation: str = "sample_pt"
    database_backend: Literal["sqlite", "postgres"] = "sqlite"
    database_url: str = ""
    database_file_name: str = "saint_jerome.db"
    database_pool_min_size: int = 1
    database_pool_max_size: int = 5
    liturgy_api_base_url: str = "https://liturgia.up.railway.app/v2/"
    liturgy_request_timeout_seconds: float = 15.0
    default_timezone: str = "America/Sao_Paulo"
    sync_commands_on_startup: bool = True

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def sample_data_file(self) -> Path:
        return self.data_dir / "sample_passages.json"

    @property
    def database_file(self) -> Path:
        return self.data_dir / self.database_file_name

    @property
    def uses_postgres(self) -> bool:
        return self.database_backend == "postgres"

    @model_validator(mode="after")
    def validate_database_settings(self) -> "Settings":
        if self.uses_postgres and not self.database_url.strip():
            raise ValueError(
                "DATABASE_URL precisa ser definido quando DATABASE_BACKEND=postgres."
            )

        if self.database_pool_min_size < 1:
            raise ValueError("DATABASE_POOL_MIN_SIZE deve ser maior ou igual a 1.")

        if self.database_pool_max_size < self.database_pool_min_size:
            raise ValueError(
                "DATABASE_POOL_MAX_SIZE deve ser maior ou igual a DATABASE_POOL_MIN_SIZE."
            )

        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
