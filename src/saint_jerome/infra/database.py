from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg
else:
    try:
        import asyncpg
    except ModuleNotFoundError:  # pragma: no cover - depends on optional runtime setup
        asyncpg = None  # type: ignore[assignment]


@dataclass(slots=True)
class PostgresPoolFactory:
    dsn: str
    min_size: int = 1
    max_size: int = 5
    command_timeout: float = 30.0
    _pool: "asyncpg.Pool | None" = field(default=None, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    async def get_pool(self) -> "asyncpg.Pool":
        if asyncpg is None:
            raise RuntimeError(
                "O suporte a PostgreSQL requer a dependência 'asyncpg' instalada."
            )

        if self._pool is not None:
            return self._pool

        async with self._lock:
            if self._pool is None:
                self._pool = await asyncpg.create_pool(
                    dsn=self.dsn,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    command_timeout=self.command_timeout,
                )

        return self._pool

    async def close(self) -> None:
        if self._pool is None:
            return

        await self._pool.close()
        self._pool = None
