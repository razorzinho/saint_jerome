from __future__ import annotations

import pytest

from saint_jerome.config.settings import Settings


def test_settings_require_database_url_for_postgres() -> None:
    with pytest.raises(ValueError):
        Settings(
            discord_token="token",
            database_backend="postgres",
            database_url="",
        )


def test_settings_allow_sqlite_without_database_url() -> None:
    settings = Settings(
        discord_token="token",
        database_backend="sqlite",
        database_url="",
    )

    assert settings.uses_postgres is False
