from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from saint_jerome.app.services.liturgy_service import LiturgyClient


class LiturgyApiError(RuntimeError):
    """Raised when the remote liturgy API request fails."""


@dataclass(slots=True)
class RailwayLiturgyClient(LiturgyClient):
    base_url: str
    timeout_seconds: float = 15.0

    async def fetch_today(self) -> dict:
        return await self._request_json({})

    async def fetch_by_date(
        self,
        *,
        day: int,
        month: int | None = None,
        year: int | None = None,
    ) -> dict:
        params: dict[str, str] = {"dia": f"{day:02d}"}
        if month is not None:
            params["mes"] = f"{month:02d}"
        if year is not None:
            params["ano"] = str(year)
        return await self._request_json(params)

    async def fetch_period(self, days: int) -> list[dict]:
        payload = await self._request_json({"periodo": str(days)})
        if not isinstance(payload, list):
            raise LiturgyApiError("A API retornou um formato inesperado para o período.")
        return payload

    async def _request_json(self, params: dict[str, str]) -> dict | list[dict]:
        return await asyncio.to_thread(self._request_json_sync, params)

    def _request_json_sync(self, params: dict[str, str]) -> dict | list[dict]:
        query = urlencode(params)
        separator = "&" if "?" in self.base_url else "?"
        url = self.base_url if not query else f"{self.base_url}{separator}{query}"
        request = Request(url, headers={"Accept": "application/json"})

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise LiturgyApiError(
                f"Falha ao consultar a liturgia ({exc.code}): {body or exc.reason}"
            ) from exc
        except URLError as exc:
            raise LiturgyApiError(
                "Não foi possível conectar à API da liturgia."
            ) from exc

        if isinstance(payload, dict) and payload.get("erro"):
            raise LiturgyApiError(str(payload["erro"]))
        return payload
