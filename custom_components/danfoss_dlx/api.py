"""Minimal client for the Danfoss DLX built-in ("Theia") web server."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=10)


class DlxApiError(Exception):
    """Raised when the inverter can't be reached or returns something unexpected."""


@dataclass
class DlxSystemInfo:
    """One entry from file/systemList.json."""

    name: str
    system: int
    system_type: int
    nominal_power: int

    @property
    def is_power_plant(self) -> bool:
        """Mirror the vendor JS: Theia.Inverter.isPowerPlant()."""
        return self.system == 17 and self.system_type == 1


class DlxApiClient:
    """Talk to the inverter's local JSON-RPC / eNEXUS interface."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        self._host = host
        self._session = session
        self._base = f"http://{host}"

    async def async_get_systems(self) -> list[DlxSystemInfo]:
        """Fetch the list of systems (inverters / plant) known to this web server."""
        url = f"{self._base}/file/systemList.json"
        try:
            async with self._session.get(url, timeout=TIMEOUT) as resp:
                if resp.status != 200:
                    raise DlxApiError(f"HTTP {resp.status} from {url}")
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise DlxApiError(f"Cannot reach {self._host}: {err}") from err

        return [
            DlxSystemInfo(
                name=item["Text"],
                system=item["system"],
                system_type=item["systemType"],
                nominal_power=item["nominalPower"],
            )
            for item in data
        ]

    async def async_get_default_inverter(self) -> DlxSystemInfo:
        """Return the first real inverter (skip the aggregated "Plant" entry)."""
        systems = await self.async_get_systems()
        for system in systems:
            if not system.is_power_plant:
                return system
        if systems:
            return systems[0]
        raise DlxApiError("Inverter returned an empty system list")

    async def async_get_power_log(
        self,
        system: int,
        system_type: int,
        start: datetime,
        unit: str,
        resolution: str,
        count: int,
    ) -> list[float]:
        """Read the inverter's own production log.

        Resolutions: "15min", "1day", "1mnd". Note that despite the "Wh" unit,
        15min samples are an *average power in W* over each interval, so the
        caller must multiply by 0.25 h to get energy. The 1day/1mnd resolutions
        do return energy in kWh. Returns [] for periods outside the log.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "GetPowerLog",
            "params": [
                system_type,
                system,
                start.strftime("%Y-%m-%d %H:%M:%S"),
                unit,
                resolution,
                count,
            ],
            "id": 0,
        }
        result = await self._async_rpc("GetPowerLog", payload)
        return result.get("Values", [])

    async def async_read(
        self, points: list[tuple[str, str]]
    ) -> dict[str, str]:
        """Batch-read eNEXUS paths.

        `points` is a list of (path, datatype) tuples, e.g.
        [("eNEXUS_0010[s:1,t:17]", "INT16U"), ...].
        Returns a dict of path -> raw string value.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "GeteNexusData",
            "params": [{"path": path, "datatype": datatype} for path, datatype in points],
            "id": 0,
        }
        result = await self._async_rpc("GeteNexusData", payload)
        return {item["path"]: item["value"] for item in result}

    async def _async_rpc(self, method: str, payload: dict[str, Any]) -> Any:
        """POST a JSON-RPC call and return its `result` member."""
        url = f"{self._base}/rpc/{method}"
        try:
            async with self._session.post(url, json=payload, timeout=TIMEOUT) as resp:
                if resp.status != 200:
                    raise DlxApiError(f"HTTP {resp.status} from {url}")
                data: dict[str, Any] = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise DlxApiError(f"Cannot reach {self._host}: {err}") from err

        if "result" not in data:
            raise DlxApiError(f"Unexpected response: {data}")

        return data["result"]
