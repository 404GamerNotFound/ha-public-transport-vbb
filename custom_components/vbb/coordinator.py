"""Data update coordinator for the VBB departures integration.

One coordinator exists per station. It performs a single API request per
update interval and every sensor of that station reads from the shared result,
instead of each sensor polling the API on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import VbbApiError, async_request_json
from .const import API_PATH, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StationConfig:
    """Static configuration of a monitored station."""

    station_id: str
    name: str
    duration: int
    results: int
    products: frozenset[str]
    update_interval: int  # minutes


@dataclass(slots=True)
class Departure:
    """A single upcoming departure, already parsed and normalised."""

    time: datetime  # realtime departure (falls back to planned), UTC
    planned: datetime | None
    line: str | None
    product: str | None
    destination: str | None
    direction: str | None
    raw: dict[str, Any] = field(repr=False)

    @property
    def delay_minutes(self) -> int | None:
        return get_delay_minutes(self.raw)

    def summary(self, *, with_line: bool = False) -> dict[str, Any]:
        """Compact attribute representation of this departure."""
        data: dict[str, Any] = {
            "when": self.time.isoformat(),
            "planned_when": self.planned.isoformat() if self.planned else None,
            "delay": self.delay_minutes,
            "platform": self.raw.get("platform"),
            "destination": self.destination,
        }
        if with_line:
            data["line"] = self.line
        else:
            data["trip_id"] = self.raw.get("tripId")
            data["prognosis_type"] = self.raw.get("prognosisType")
        return data


def get_delay_minutes(entry: dict[str, Any]) -> int | None:
    """Return the delay in whole minutes.

    transport.rest reports ``delay`` in seconds; ``0`` means "on time" and must
    not be treated as missing.
    """
    for key in ("delay", "departureDelay", "delayInSeconds"):
        value = entry.get(key)
        if value is not None:
            try:
                return round(int(value) / 60)
            except (TypeError, ValueError):
                return None
    return None


def parse_time(value: str | None) -> datetime | None:
    """Parse a departure timestamp and normalise it to UTC."""
    if not value:
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    try:
        return dt_util.as_utc(parsed)
    except (TypeError, ValueError):
        return None


def extract_departures(data: Any) -> list[dict[str, Any]]:
    """Normalise the API payload (v5 list or v6 object) to a list."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("departures"), list):
        return data["departures"]
    return []


def parse_departures(data: Any, products: frozenset[str]) -> list[Departure]:
    """Turn the raw API payload into sorted, upcoming, non-cancelled departures."""
    now = dt_util.utcnow()
    result: list[Departure] = []
    for raw in extract_departures(data):
        if not isinstance(raw, dict) or raw.get("cancelled"):
            continue
        line_info = raw.get("line") or {}
        product = line_info.get("product")
        if product and product not in products:
            continue
        planned = parse_time(raw.get("plannedWhen") or raw.get("plannedDeparture"))
        time = parse_time(raw.get("when") or raw.get("departure")) or planned
        if time is None or time <= now:
            continue
        result.append(
            Departure(
                time=time,
                planned=planned,
                line=line_info.get("name"),
                product=product,
                destination=(raw.get("destination") or {}).get("name")
                or raw.get("direction"),
                direction=raw.get("direction"),
                raw=raw,
            )
        )
    result.sort(key=lambda dep: dep.time)
    return result


class VbbCoordinator(DataUpdateCoordinator[list[Departure]]):
    """Fetch departures for one station once per interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        station: StationConfig,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN} {station.name}",
            update_interval=timedelta(minutes=station.update_interval),
        )
        self.station = station
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> list[Departure]:
        params = {
            "duration": self.station.duration,
            "results": self.station.results,
        }
        try:
            data = await async_request_json(
                self._session,
                API_PATH.format(station=self.station.station_id),
                params,
            )
        except VbbApiError as err:
            raise UpdateFailed(str(err)) from err
        return parse_departures(data, self.station.products)
