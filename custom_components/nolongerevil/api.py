"""NoLongerEvil REST API client."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://nolongerevil.com/api/v1"
TIMEOUT = aiohttp.ClientTimeout(total=30)


class NLEAuthError(Exception):
    """Authentication error."""


class NLEConnectionError(Exception):
    """Connection error."""


class NLERateLimitError(Exception):
    """Rate limit exceeded."""


class NLEApiClient:
    """Client for the NoLongerEvil REST API."""

    def __init__(
        self,
        api_key: str,
        session: aiohttp.ClientSession,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self._api_key = api_key
        self._session = session
        self._base_url = base_url.rstrip("/")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method, url, headers=self._headers, json=json, timeout=TIMEOUT
            ) as resp:
                if resp.status == 401:
                    raise NLEAuthError("Invalid API key or insufficient permissions")
                if resp.status == 429:
                    raise NLERateLimitError("NLE API rate limit exceeded (20 req/min)")
                if resp.status == 404:
                    raise NLEConnectionError(f"NLE endpoint not found: {path}")
                if resp.status >= 500:
                    text = await resp.text()
                    raise NLEConnectionError(f"NLE server error {resp.status}: {text}")
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise NLEConnectionError(f"Cannot connect to NLE API: {err}") from err

    # ── Device discovery ──────────────────────────────────────────────────────

    async def list_devices(self) -> list[dict]:
        """Return all devices for the account."""
        data = await self._request("GET", "/devices")
        # API returns a list or {"devices": [...]}
        if isinstance(data, list):
            return data
        return data.get("devices", [])

    # ── Device status ─────────────────────────────────────────────────────────

    async def get_status(self, device_id: str) -> dict:
        """Return full status for one device."""
        return await self._request("GET", f"/thermostat/{device_id}/status")

    # ── Temperature control ───────────────────────────────────────────────────

    async def set_temperature(
        self,
        device_id: str,
        value: float,
        mode: str,
        scale: str = "C",
    ) -> dict:
        """Set a single target temperature."""
        return await self._request(
            "POST",
            f"/thermostat/{device_id}/temperature",
            json={"value": value, "mode": mode, "scale": scale},
        )

    async def set_temperature_range(
        self,
        device_id: str,
        heat: float,
        cool: float,
        scale: str = "C",
    ) -> dict:
        """Set heat/cool temperature range for auto mode."""
        return await self._request(
            "POST",
            f"/thermostat/{device_id}/temperature/range",
            json={"heatValue": heat, "coolValue": cool, "scale": scale},
        )

    # ── HVAC mode ─────────────────────────────────────────────────────────────

    async def set_mode(self, device_id: str, mode: str) -> dict:
        """Set HVAC mode: heat | cool | auto | off."""
        return await self._request(
            "POST",
            f"/thermostat/{device_id}/mode",
            json={"mode": mode},
        )

    # ── Away mode ─────────────────────────────────────────────────────────────

    async def set_away(self, device_id: str, away: bool) -> dict:
        """Enable or disable away mode."""
        return await self._request(
            "POST",
            f"/thermostat/{device_id}/away",
            json={"away": away},
        )

    # ── Fan control ───────────────────────────────────────────────────────────

    async def set_fan(self, device_id: str, mode: str, duration: int | None = None) -> dict:
        """Control the fan.

        mode: 'on' | 'auto'
        duration: optional timer in seconds
        """
        payload: dict = {"mode": mode}
        if duration is not None:
            payload["duration"] = duration
        return await self._request(
            "POST",
            f"/thermostat/{device_id}/fan",
            json=payload,
        )

    # ── Temperature lock ──────────────────────────────────────────────────────

    async def set_lock(
        self,
        device_id: str,
        enabled: bool,
        pin: str | None = None,
        min_temp: float | None = None,
        max_temp: float | None = None,
    ) -> dict:
        """Enable or disable temperature lock."""
        payload: dict = {"enabled": enabled}
        if pin is not None:
            payload["pin"] = pin
        if min_temp is not None:
            payload["minTemp"] = min_temp
        if max_temp is not None:
            payload["maxTemp"] = max_temp
        return await self._request(
            "POST",
            f"/thermostat/{device_id}/lock",
            json=payload,
        )

    # ── Schedule ──────────────────────────────────────────────────────────────

    async def get_schedule(self, device_id: str) -> dict:
        """Get the current schedule."""
        return await self._request("GET", f"/thermostat/{device_id}/schedule")

    async def set_schedule(self, device_id: str, schedule: dict) -> dict:
        """Update the schedule."""
        return await self._request(
            "PUT",
            f"/thermostat/{device_id}/schedule",
            json=schedule,
        )
