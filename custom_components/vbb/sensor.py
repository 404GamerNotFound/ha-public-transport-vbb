"""Sensor platform for VBB public transport departures."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import async_timeout
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
from homeassistant.util import slugify

from .const import (
    API_URL,
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
    HEADERS,
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
        url = API_URL.format(station=station_id, duration=duration, results=results)
        try:
            async with async_timeout.timeout(10):
                resp = await session.get(url, headers=HEADERS)
                resp.raise_for_status()
                data = await resp.json()
        except Exception:
            return

        sensors: list[SensorEntity] = []
        for d in data:
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
        url = API_URL.format(
            station=self._station_id, duration=self._duration, results=self._results
        )
        try:
            async with async_timeout.timeout(10):
                resp = await self._session.get(url, headers=HEADERS)
                resp.raise_for_status()
                data = await resp.json()
        except Exception:
            self._attr_available = False
            return

        self._attr_available = True

        departures: list[dict[str, Any]] = []
        for d in data:
            if d.get("line", {}).get("name") != self._line:
                continue
            dest_info = d.get("destination") or {}
            dest_name = dest_info.get("name") or d.get("direction")
            if dest_name != self._destination:
                continue
            when = _get_time(d)
            if not when:
                continue
            try:
                dep_time = datetime.fromisoformat(when)
            except ValueError:
                continue
            if dep_time <= datetime.now(dep_time.tzinfo or timezone.utc):
                continue
            departures.append(d)

        if not departures:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return

        departures.sort(key=_get_time)
        first = departures[0]
        self._station_name = first.get("stop", {}).get("name", self._station_name)
        self._direction = first.get("direction")
        dest_info = first.get("destination") or {}
        destination_name = dest_info.get("name") or self._destination
        when = _get_time(first)
        if when:
            try:
                self._attr_native_value = datetime.fromisoformat(when)
            except ValueError:
                self._attr_native_value = when
        else:
            self._attr_native_value = None

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
                for d in departures
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
        url = API_URL.format(
            station=self._station_id, duration=self._duration, results=self._results
        )
        try:
            async with async_timeout.timeout(10):
                resp = await self._session.get(url, headers=HEADERS)
                resp.raise_for_status()
                data = await resp.json()
        except Exception:
            self._attr_available = False
            return

        self._attr_available = True

        departures: list[dict[str, Any]] = []
        for d in data:
            if d.get("line", {}).get("name") != self._line:
                continue
            if d.get("direction") != self._direction:
                continue
            when = _get_time(d)
            if not when:
                continue
            try:
                dep_time = datetime.fromisoformat(when)
            except ValueError:
                continue
            if dep_time <= datetime.now(dep_time.tzinfo or timezone.utc):
                continue
            departures.append(d)

        if not departures:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return

        departures.sort(key=_get_time)
        first = departures[0]
        self._station_name = first.get("stop", {}).get("name", self._station_name)
        dest_info = first.get("destination") or {}
        destination_name = dest_info.get("name")
        when = _get_time(first)
        if when:
            try:
                self._attr_native_value = datetime.fromisoformat(when)
            except ValueError:
                self._attr_native_value = when
        else:
            self._attr_native_value = None

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
                for d in departures
            ],
        }
