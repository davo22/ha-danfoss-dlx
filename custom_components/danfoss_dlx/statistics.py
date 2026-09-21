"""Backfill of Home Assistant long-term statistics from the inverter's own log.

The DLX keeps its own production history and serves it over the same JSON-RPC
interface the web UI uses, at three resolutions:

* ``15min`` — roughly the last 100 days. Despite reporting a "Wh" unit these
  samples are an *average power in W* per interval, so energy = value * 0.25 h.
  (Verified against the daily figures: agreement is better than 0.1%.)
* ``1day``  — the current calendar year, in kWh per day.
* ``1mnd``  — the full history back to commissioning, in kWh per month.

Those are imported as an external statistic, so the recorder's own statistics
for the sensor entities are left untouched.
"""
from __future__ import annotations

import logging
from calendar import monthrange
from datetime import datetime, timedelta

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .api import DlxApiClient, DlxApiError, DlxSystemInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# 15-minute samples are average power, so each represents a quarter hour.
QUARTER_HOUR = 0.25

# How far back to try the high-resolution log before falling back to daily data.
MAX_QUARTER_HOUR_DAYS = 120

# The daily log only covers the current calendar year, but ask a little wider
# in case other firmware keeps more; the empty-response counter stops the walk.
MAX_DAILY_MONTHS = 36

# Stop walking backwards after this many consecutive periods with no data.
MAX_EMPTY_PERIODS = 2
MAX_HISTORY_YEARS = 25


def build_statistic_id(system_info: DlxSystemInfo) -> str:
    """Return the external statistic id used for this inverter's history."""
    serial = system_info.name.split(" - ")[0].strip().lower()
    slug = "".join(c if c.isalnum() else "_" for c in serial) or "inverter"
    return f"{DOMAIN}:{slug}_energy_production_history"


async def async_has_history(hass: HomeAssistant, statistic_id: str) -> bool:
    """Return True if this statistic has already been imported."""
    last = await get_instance(hass).async_add_executor_job(
        get_last_statistics, hass, 1, statistic_id, True, {"sum"}
    )
    return bool(last.get(statistic_id))


async def async_import_history(
    hass: HomeAssistant,
    client: DlxApiClient,
    system_info: DlxSystemInfo,
    end: datetime,
) -> int:
    """Import production history up to (excluding) `end`.

    `end` should be the hour at which the live sensor entities take over, so
    that the imported history and the recorder's own statistics don't overlap.
    Returns the number of hourly points written.
    """
    statistic_id = build_statistic_id(system_info)
    cutoff = end.replace(minute=0, second=0, microsecond=0)

    hourly = await _async_collect(client, system_info, cutoff)
    if not hourly:
        _LOGGER.warning("Inverter returned no usable history")
        return 0

    running_sum = 0.0
    points: list[StatisticData] = []
    for start in sorted(hourly):
        running_sum += hourly[start]
        points.append(StatisticData(start=start, state=hourly[start], sum=running_sum))

    metadata = StatisticMetaData(
        has_mean=False,
        has_sum=True,
        name=f"{system_info.name} production history",
        source=DOMAIN,
        statistic_id=statistic_id,
        unit_of_measurement="kWh",
    )
    async_add_external_statistics(hass, metadata, points)

    _LOGGER.info(
        "Imported %s hourly points (%.1f kWh) of history from %s to %s",
        len(points),
        running_sum,
        points[0]["start"].isoformat(),
        points[-1]["start"].isoformat(),
    )
    return len(points)


async def _async_collect(
    client: DlxApiClient, system_info: DlxSystemInfo, cutoff: datetime
) -> dict[datetime, float]:
    """Collect hourly energy, preferring the finest resolution available.

    Each period is taken from exactly one resolution, so nothing is counted
    twice: days covered by 15-minute samples are skipped by the daily pass, and
    months that the daily pass filled are skipped by the monthly pass. A month
    that only the 15-minute log reached partially is replaced wholesale by its
    monthly total, which is the more complete figure.
    """
    hourly: dict[datetime, float] = {}
    days_from_quarter_hour: set[tuple[int, int, int]] = set()
    months_from_daily: set[tuple[int, int]] = set()

    today = dt_util.now().date()

    # 1. High-resolution samples, for as far back as the inverter keeps them.
    for offset in range(MAX_QUARTER_HOUR_DAYS):
        day = today - timedelta(days=offset)
        local_midnight = _local(day.year, day.month, day.day)
        values = await _async_log(
            client, system_info, local_midnight, "Wh", "15min", 96
        )
        if not values or not any(values):
            continue

        for hour in range(24):
            energy = sum(values[hour * 4 : hour * 4 + 4]) * QUARTER_HOUR / 1000
            if energy <= 0:
                continue
            start = dt_util.as_utc(local_midnight + timedelta(hours=hour))
            if start < cutoff:
                hourly[start] = energy

        days_from_quarter_hour.add((day.year, day.month, day.day))

    # 2. Daily totals, for every month the daily log still covers.
    empty_months = 0
    for year, month in _months_back(today, MAX_DAILY_MONTHS):
        values = await _async_log(
            client,
            system_info,
            _local(year, month, 1),
            "kWh",
            "1day",
            monthrange(year, month)[1],
        )
        if not values:
            empty_months += 1
            if empty_months >= MAX_EMPTY_PERIODS:
                break
            continue

        empty_months = 0
        if not any(values):
            continue

        for index, energy in enumerate(values):
            day_number = index + 1
            if energy <= 0 or (year, month, day_number) in days_from_quarter_hour:
                continue
            start = dt_util.as_utc(_local(year, month, day_number, hour=12))
            if start < cutoff:
                hourly[start] = hourly.get(start, 0) + energy

        months_from_daily.add((year, month))

    # 3. Monthly totals for everything older than the daily log reaches.
    empty_years = 0
    for year in range(today.year, today.year - MAX_HISTORY_YEARS, -1):
        values = await _async_log(
            client, system_info, _local(year, 1, 1), "kWh", "1mnd", 12
        )
        if not values or not any(values):
            empty_years += 1
            if empty_years >= MAX_EMPTY_PERIODS:
                break
            continue

        empty_years = 0
        for index, energy in enumerate(values):
            month = index + 1
            if energy <= 0 or (year, month) in months_from_daily:
                continue
            _drop_month(hourly, year, month)
            start = dt_util.as_utc(_local(year, month, 15, hour=12))
            if start < cutoff:
                hourly[start] = energy

    return hourly


async def _async_log(
    client: DlxApiClient,
    system_info: DlxSystemInfo,
    start: datetime,
    unit: str,
    resolution: str,
    count: int,
) -> list[float]:
    """Fetch one page of the production log, treating errors as no data."""
    try:
        return await client.async_get_power_log(
            system_info.system, system_info.system_type, start, unit, resolution, count
        )
    except DlxApiError as err:
        _LOGGER.debug("%s log at %s failed: %s", resolution, start.date(), err)
        return []


def _drop_month(hourly: dict[datetime, float], year: int, month: int) -> None:
    """Remove partial hourly data for a month about to be replaced by its total."""
    for start in [
        start
        for start in hourly
        if (local := dt_util.as_local(start)).year == year and local.month == month
    ]:
        del hourly[start]


def _local(year: int, month: int, day: int, hour: int = 0) -> datetime:
    """Build a local-time datetime; the inverter's clock runs local time."""
    return datetime(year, month, day, hour, tzinfo=dt_util.DEFAULT_TIME_ZONE)


def _months_back(today, count: int):
    """Yield (year, month) pairs going backwards from the current month."""
    year, month = today.year, today.month
    for _ in range(count):
        yield year, month
        month -= 1
        if month == 0:
            year, month = year - 1, 12
