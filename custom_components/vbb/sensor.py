"""Sensor platform for VBB public transport departures."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from collections import defaultdict

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
from homeassistant.util import slugify

from .const import (
    API_URL,
    CONF_DURATION,
    CONF_RESULTS,
    CONF_STATION_ID,
    DEFAULT_DURATION,
    DEFAULT_NAME,
    DEFAULT_RESULTS,
    DOMAIN,
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
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the VBB sensor platform."""
    station_id = config[CONF_STATION_ID]
    name = config[CONF_NAME]
    duration = config.get(CONF_DURATION, DEFAULT_DURATION)
    results = config.get(CONF_RESULTS, DEFAULT_RESULTS)
    session = async_get_clientsession(hass)
    url = API_URL.format(station=station_id, duration=duration, results=results)
    async with async_timeout.timeout(10):
        resp = await session.get(url)
        data = await resp.json()
    lines: dict[str, set[str]] = defaultdict(set)
    for d in data:
        line = d.get("line", {}).get("name")
        dest_info = d.get("destination") or {}
        destination = dest_info.get("name") or d.get("direction")
        if line and destination:
            lines[line].add(destination)
    sensors = [
        VbbDepartureSensor(hass, station_id, name, line, dest, duration, results)
        for line, destinations in lines.items()
        for dest in destinations
    ]
    async_add_entities(sensors, True)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up VBB sensor from a config entry."""
    station_id = entry.data[CONF_STATION_ID]
    name = entry.data[CONF_NAME]
    duration = entry.data.get(CONF_DURATION, DEFAULT_DURATION)
    results = entry.data.get(CONF_RESULTS, DEFAULT_RESULTS)
    session = async_get_clientsession(hass)
    url = API_URL.format(station=station_id, duration=duration, results=results)
    async with async_timeout.timeout(10):
        resp = await session.get(url)
        data = await resp.json()
    lines: dict[str, set[str]] = defaultdict(set)
    for d in data:
        line = d.get("line", {}).get("name")
        dest_info = d.get("destination") or {}
        destination = dest_info.get("name") or d.get("direction")
        if line and destination:
            lines[line].add(destination)
    sensors = [
        VbbDepartureSensor(hass, station_id, name, line, dest, duration, results)
        for line, destinations in lines.items()
        for dest in destinations
    ]
    async_add_entities(sensors, True)


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
        async with async_timeout.timeout(10):
            resp = await self._session.get(url)
            data = await resp.json()

        departures: list[dict[str, Any]] = []
        for d in data:
            if d.get("line", {}).get("name") != self._line:
                continue
            dest_info = d.get("destination") or {}
            dest_name = dest_info.get("name") or d.get("direction")
            if dest_name != self._destination:
                continue
            when = d.get("plannedWhen") or d.get("when")
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

        departures.sort(key=lambda d: d.get("plannedWhen") or d.get("when"))
        first = departures[0]
        self._station_name = first.get("stop", {}).get("name", self._station_name)
        self._direction = first.get("direction")
        dest_info = first.get("destination") or {}
        destination_name = dest_info.get("name") or self._destination
        when = first.get("plannedWhen") or first.get("when")
        if when:
            try:
                self._attr_native_value = datetime.fromisoformat(when)
            except ValueError:
                self._attr_native_value = when
        else:
            self._attr_native_value = None

        stop = first.get("stop", {})
        location = stop.get("location", {})
        line_info = first.get("line", {})
        origin_info = first.get("origin", {})
        current_pos = first.get("currentTripPosition", {})
        delay = first.get("delay")
        delay = delay // 60 if delay is not None else None

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
                    "when": d.get("plannedWhen") or d.get("when"),
                    "delay": (
                        d.get("delay") // 60 if d.get("delay") is not None else None
                    ),
                    "platform": d.get("platform"),
                    "destination": (d.get("destination") or {}).get("name"),
                    "trip_id": d.get("tripId"),
                    "prognosis_type": d.get("prognosisType"),
                }
                for d in departures
            ],
        }
