from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    discord_token: str = Field(default="")
    default_translation: str = "sample_pt"
    database_file_name: str = "saint_jerome.db"
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
