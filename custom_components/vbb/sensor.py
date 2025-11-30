"""Sensor platform for VBB public transport departures."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import slugify, dt as dt_util

from .api import async_request_json
from .const import (
    API_PATH,
    CONF_DURATION,
    CONF_PRODUCTS,
    CONF_RESULTS,
    CONF_STATION_ID,
    DEFAULT_DURATION,
    DEFAULT_PRODUCTS,
    DEFAULT_NAME,
    DEFAULT_RESULTS,
    DOMAIN,
    PRODUCT_OPTIONS,
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_STATION_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DURATION, default=DEFAULT_DURATION): vol.All(
            int, vol.Range(min=1)
        ),
        vol.Optional(CONF_RESULTS, default=DEFAULT_RESULTS): vol.All(
            int, vol.Range(min=1)
        ),
        vol.Optional(
            CONF_PRODUCTS, default=DEFAULT_PRODUCTS
        ): vol.All(cv.ensure_list, [vol.In(PRODUCT_OPTIONS)]),
    }
)


def _get_time(entry: dict[str, Any]) -> str | None:
    """Return the best available departure time field."""
    return (
        entry.get("plannedWhen")
        or entry.get("when")
        or entry.get("plannedDeparture")
        or entry.get("departure")
    )


def _get_delay(entry: dict[str, Any]) -> int | None:
    """Return delay in minutes if available."""
    delay = (
        entry.get("delay")
        or entry.get("departureDelay")
        or entry.get("delayInSeconds")
    )
    if delay is None:
        return None
    if isinstance(delay, int) and abs(delay) > 10:
        return delay // 60
    return delay


def _extract_departures(data: Any) -> list[dict[str, Any]]:
    """Normalize API responses to a departures list."""

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        departures = data.get("departures")
        if isinstance(departures, list):
            return departures

    return []


def _parse_departure_time(value: str | None) -> datetime | None:
    """Parse a departure timestamp and normalize it to UTC."""

    if not value:
        return None

    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None

    try:
        return dt_util.as_utc(parsed)
    except (TypeError, ValueError):
        return None


async def _async_setup_station(
    hass,
    station_id: str,
    name: str,
    duration: int,
    results: int,
    products: list[str],
    async_add_entities,
) -> None:
    """Set up sensors for a station and add new ones dynamically."""
    session = async_get_clientsession(hass)
    known_pairs: set[tuple[str, str]] = set()
    known_dirs: set[tuple[str, str]] = set()

    async def discover(now=None):
        params = {"duration": duration, "results": results}
        try:
            data = await async_request_json(
                session, API_PATH.format(station=station_id), params
            )
        except Exception:
            return

        sensors: list[SensorEntity] = []
        departures = _extract_departures(data)

        for d in departures:
            line_info = d.get("line") or {}
            if line_info.get("product") not in products:
                continue
            line = line_info.get("name")
            dest_info = d.get("destination") or {}
            destination = dest_info.get("name") or d.get("direction")
            direction = d.get("direction")
            if line and destination and (line, destination) not in known_pairs:
                known_pairs.add((line, destination))
                sensors.append(
                    VbbDepartureSensor(
                        hass, station_id, name, line, destination, duration, results
                    )
                )
            if line and direction and (line, direction) not in known_dirs:
                known_dirs.add((line, direction))
                sensors.append(
                    VbbDirectionSensor(
                        hass, station_id, name, line, direction, duration, results
                    )
                )

        if sensors:
            async_add_entities(sensors, True)

    await discover()
    async_track_time_interval(hass, discover, timedelta(minutes=5))


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the VBB sensor platform."""
    station_id = config[CONF_STATION_ID]
    name = config[CONF_NAME]
    duration = config.get(CONF_DURATION, DEFAULT_DURATION)
    results = config.get(CONF_RESULTS, DEFAULT_RESULTS)
    products = config.get(CONF_PRODUCTS, DEFAULT_PRODUCTS)
    await _async_setup_station(
        hass, station_id, name, duration, results, products, async_add_entities
    )


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up VBB sensor from a config entry."""
    station_id = entry.data[CONF_STATION_ID]
    name = entry.data[CONF_NAME]
    duration = entry.data.get(CONF_DURATION, DEFAULT_DURATION)
    results = entry.data.get(CONF_RESULTS, DEFAULT_RESULTS)
    products = entry.options.get(
        CONF_PRODUCTS, entry.data.get(CONF_PRODUCTS, DEFAULT_PRODUCTS)
    )
    await _async_setup_station(
        hass, station_id, name, duration, results, products, async_add_entities
    )


class VbbDepartureSensor(SensorEntity):
    """Representation of a VBB departure sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:train"

    def __init__(
        self,
        hass,
        station_id: str,
        station_name: str,
        line: str,
        destination: str,
        duration: int,
        results: int,
    ) -> None:
        self.hass = hass
        self._station_id = station_id
        self._station_name = station_name
        self._line = line
        self._destination = destination
        self._direction: str | None = None
        self._duration = duration
        self._results = results
        self._attr_name = f"{line} {destination}"
        self._attr_unique_id = (
            f"vbb_{station_id}_{slugify(line)}_{slugify(destination)}"
        )
        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._session = async_get_clientsession(hass)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._station_id)},
            name=self._station_name,
            manufacturer="VBB",
        )

    async def async_update(self) -> None:
        """Fetch departures from the VBB API."""
        params = {"duration": self._duration, "results": self._results}
        try:
            data = await async_request_json(
                self._session, API_PATH.format(station=self._station_id), params
            )
        except Exception:
            self._attr_available = False
            return

        self._attr_available = True

        departures: list[tuple[datetime, dict[str, Any]]] = []
        for d in _extract_departures(data):
            if d.get("line", {}).get("name") != self._line:
                continue
            dest_info = d.get("destination") or {}
            dest_name = dest_info.get("name") or d.get("direction")
            if dest_name != self._destination:
                continue
            dep_time = _parse_departure_time(_get_time(d))
            if dep_time is None:
                continue
            if dep_time <= dt_util.utcnow():
                continue
            departures.append((dep_time, d))

        if not departures:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return

        departures.sort(key=lambda item: item[0])
        first_time, first = departures[0]
        self._station_name = first.get("stop", {}).get("name", self._station_name)
        self._direction = first.get("direction")
        dest_info = first.get("destination") or {}
        destination_name = dest_info.get("name") or self._destination
        self._attr_native_value = first_time

        stop = first.get("stop") or {}
        location = stop.get("location") or {}
        line_info = first.get("line") or {}
        origin_info = first.get("origin") or {}
        current_pos = first.get("currentTripPosition") or None
        delay = _get_delay(first)

        self._attr_extra_state_attributes = {
            "line": self._line,
            "destination": destination_name,
            "direction": self._direction,
            "station_id": self._station_id,
            "station_name": stop.get("name"),
            "station_dhid": stop.get("stationDHID"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "line_id": line_info.get("id"),
            "mode": line_info.get("mode"),
            "product": line_info.get("product"),
            "operator": line_info.get("operator", {}).get("name"),
            "trip_id": first.get("tripId"),
            "delay": delay,
            "prognosis_type": first.get("prognosisType"),
            "origin": origin_info.get("name"),
            "current_trip_position": current_pos or None,
            "departures": [
                {
                    "when": _get_time(d),
                    "delay": _get_delay(d),
                    "platform": d.get("platform"),
                    "destination": (d.get("destination") or {}).get("name"),
                    "trip_id": d.get("tripId"),
                    "prognosis_type": d.get("prognosisType"),
                }
                for _, d in departures
            ],
        }


class VbbDirectionSensor(SensorEntity):
    """Representation of a VBB direction sensor aggregating all destinations."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:train"

    def __init__(
        self,
        hass,
        station_id: str,
        station_name: str,
        line: str,
        direction: str,
        duration: int,
        results: int,
    ) -> None:
        self.hass = hass
        self._station_id = station_id
        self._station_name = station_name
        self._line = line
        self._direction = direction
        self._duration = duration
        self._results = results
        self._attr_name = f"{line} {direction}"
        self._attr_unique_id = (
            f"vbb_{station_id}_{slugify(line)}_{slugify(direction)}_dir"
        )
        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._session = async_get_clientsession(hass)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._station_id)},
            name=self._station_name,
            manufacturer="VBB",
        )

    async def async_update(self) -> None:
        """Fetch departures from the VBB API."""
        params = {"duration": self._duration, "results": self._results}
        try:
            data = await async_request_json(
                self._session, API_PATH.format(station=self._station_id), params
            )
        except Exception:
            self._attr_available = False
            return

        self._attr_available = True

        departures: list[tuple[datetime, dict[str, Any]]] = []
        for d in _extract_departures(data):
            if d.get("line", {}).get("name") != self._line:
                continue
            if d.get("direction") != self._direction:
                continue
            dep_time = _parse_departure_time(_get_time(d))
            if dep_time is None:
                continue
            if dep_time <= dt_util.utcnow():
                continue
            departures.append((dep_time, d))

        if not departures:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return

        departures.sort(key=lambda item: item[0])
        first_time, first = departures[0]
        self._station_name = first.get("stop", {}).get("name", self._station_name)
        dest_info = first.get("destination") or {}
        destination_name = dest_info.get("name")
        self._attr_native_value = first_time

        stop = first.get("stop") or {}
        location = stop.get("location") or {}
        line_info = first.get("line") or {}
        origin_info = first.get("origin") or {}
        current_pos = first.get("currentTripPosition") or None
        delay = _get_delay(first)

        self._attr_extra_state_attributes = {
            "line": self._line,
            "direction": self._direction,
            "destination": destination_name,
            "station_id": self._station_id,
            "station_name": stop.get("name"),
            "station_dhid": stop.get("stationDHID"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "line_id": line_info.get("id"),
            "mode": line_info.get("mode"),
            "product": line_info.get("product"),
            "operator": line_info.get("operator", {}).get("name"),
            "trip_id": first.get("tripId"),
            "delay": delay,
            "prognosis_type": first.get("prognosisType"),
            "origin": origin_info.get("name"),
            "current_trip_position": current_pos or None,
            "departures": [
                {
                    "when": _get_time(d),
                    "delay": _get_delay(d),
                    "platform": d.get("platform"),
                    "destination": (d.get("destination") or {}).get("name"),
                    "trip_id": d.get("tripId"),
                    "prognosis_type": d.get("prognosisType"),
                }
                for _, d in departures
            ],
        }
