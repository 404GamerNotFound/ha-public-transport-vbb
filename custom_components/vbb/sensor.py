"""Sensor platform for VBB public transport departures."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util, slugify

from . import VbbConfigEntry
from .const import (
    CONF_DURATION,
    CONF_PRODUCTS,
    CONF_RESULTS,
    CONF_STATION_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_DURATION,
    DEFAULT_NAME,
    DEFAULT_PRODUCTS,
    DEFAULT_RESULTS,
    DEFAULT_UPDATE_INTERVAL,
    DIRECTION_SLOTS,
    DOMAIN,
    MAX_ATTRIBUTE_DEPARTURES,
    PRODUCT_OPTIONS,
)
from .coordinator import Departure, StationConfig, VbbCoordinator

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
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
            int, vol.Range(min=1)
        ),
        vol.Optional(CONF_PRODUCTS, default=DEFAULT_PRODUCTS): vol.All(
            cv.ensure_list, [vol.In(PRODUCT_OPTIONS)]
        ),
    }
)


async def async_setup_entry(
    hass: HomeAssistant, entry: VbbConfigEntry, async_add_entities
) -> None:
    """Set up VBB sensors from a config entry."""
    coordinator = entry.runtime_data
    entry.async_on_unload(_async_setup_entities(coordinator, async_add_entities))


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
) -> None:
    """Set up the VBB sensor platform from legacy YAML configuration."""
    station = StationConfig(
        station_id=config[CONF_STATION_ID],
        name=config[CONF_NAME],
        duration=config[CONF_DURATION],
        results=config[CONF_RESULTS],
        products=frozenset(config[CONF_PRODUCTS]),
        update_interval=config[CONF_UPDATE_INTERVAL],
    )
    coordinator = VbbCoordinator(hass, station)
    await coordinator.async_refresh()
    _async_setup_entities(coordinator, async_add_entities)


@callback
def _async_setup_entities(
    coordinator: VbbCoordinator, async_add_entities
) -> CALLBACK_TYPE:
    """Add the station sensor now and line sensors whenever new lines appear.

    Returns the listener's unsubscribe callback so it is removed on unload.
    """
    known_destinations: set[tuple[str, str]] = set()
    known_directions: set[tuple[str, str]] = set()

    # The station sensor always exists, even if discovery finds nothing yet.
    async_add_entities([VbbStationSensor(coordinator)])

    @callback
    def _discover() -> None:
        new_entities: list[SensorEntity] = []
        for dep in coordinator.data or []:
            if not dep.line:
                continue
            if dep.destination and (dep.line, dep.destination) not in known_destinations:
                known_destinations.add((dep.line, dep.destination))
                new_entities.append(
                    VbbDepartureSensor(coordinator, dep.line, dep.destination)
                )
            if dep.direction and (dep.line, dep.direction) not in known_directions:
                known_directions.add((dep.line, dep.direction))
                new_entities.extend(
                    VbbDirectionSensor(coordinator, dep.line, dep.direction, index)
                    for index in range(DIRECTION_SLOTS)
                )
        if new_entities:
            async_add_entities(new_entities)

    _discover()
    return coordinator.async_add_listener(_discover)


class VbbBaseSensor(CoordinatorEntity[VbbCoordinator], SensorEntity):
    """Common behaviour of all VBB timestamp sensors."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:train"
    # These change on every poll and would bloat the recorder database.
    _unrecorded_attributes = frozenset(
        {
            "departures",
            "current_trip_position",
            "trip_id",
            "delay",
            "prognosis_type",
            "latitude",
            "longitude",
        }
    )

    def __init__(self, coordinator: VbbCoordinator) -> None:
        super().__init__(coordinator)
        self._station = coordinator.station
        self._unsub_rollover: CALLBACK_TYPE | None = None
        self._attr_extra_state_attributes = {}

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._station.station_id)},
            name=self._station.name,
            manufacturer="VBB",
        )

    @property
    def available(self) -> bool:
        # Keep showing cached departures during short API outages; the
        # schedule itself does not become wrong just because one poll failed.
        return self.coordinator.data is not None

    def _matching(self) -> list[Departure]:
        """Return the upcoming departures this sensor is responsible for."""
        raise NotImplementedError

    @callback
    def _refresh_state(self) -> None:
        """Recompute state from cached data (no API call)."""
        if self._unsub_rollover is not None:
            self._unsub_rollover()
            self._unsub_rollover = None

        now = dt_util.utcnow()
        upcoming = [dep for dep in self._matching() if dep.time > now]
        selected = self._apply(upcoming)

        # When the shown departure has left, switch to the next one at once
        # instead of showing a past time until the next poll.
        if selected is not None:
            self._unsub_rollover = async_track_point_in_utc_time(
                self.hass, self._handle_rollover, selected.time
            )

    def _apply(self, upcoming: list[Departure]) -> Departure | None:
        raise NotImplementedError

    @callback
    def _handle_rollover(self, _now: datetime) -> None:
        self._unsub_rollover = None
        self._refresh_state()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._refresh_state()
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._refresh_state()
        self.async_on_remove(self._cancel_rollover)

    @callback
    def _cancel_rollover(self) -> None:
        if self._unsub_rollover is not None:
            self._unsub_rollover()
            self._unsub_rollover = None

    def _detail_attributes(self, dep: Departure) -> dict[str, Any]:
        """Attributes describing a single selected departure."""
        raw = dep.raw
        stop = raw.get("stop") or {}
        location = stop.get("location") or {}
        line_info = raw.get("line") or {}
        return {
            "line": dep.line,
            "destination": dep.destination,
            "direction": dep.direction,
            "station_id": self._station.station_id,
            "station_name": stop.get("name"),
            "station_dhid": stop.get("stationDHID"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "line_id": line_info.get("id"),
            "mode": line_info.get("mode"),
            "product": dep.product,
            "operator": (line_info.get("operator") or {}).get("name"),
            "trip_id": raw.get("tripId"),
            "planned_when": dep.planned.isoformat() if dep.planned else None,
            "delay": dep.delay_minutes,
            "platform": raw.get("platform"),
            "prognosis_type": raw.get("prognosisType"),
            "origin": (raw.get("origin") or {}).get("name"),
            "current_trip_position": raw.get("currentTripPosition") or None,
        }


class VbbStationSensor(VbbBaseSensor):
    """Next departure of any line at the station."""

    _attr_icon = "mdi:train-clock"

    def __init__(self, coordinator: VbbCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = self._station.name
        self._attr_unique_id = f"vbb_{self._station.station_id}_station"

    def _matching(self) -> list[Departure]:
        return list(self.coordinator.data or [])

    def _apply(self, upcoming: list[Departure]) -> Departure | None:
        if not upcoming:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return None
        first = upcoming[0]
        self._attr_native_value = first.time
        self._attr_extra_state_attributes = {
            "line": first.line,
            "destination": first.destination,
            "station_id": self._station.station_id,
            "station_name": (first.raw.get("stop") or {}).get("name", self._station.name),
            "product": first.product,
            "delay": first.delay_minutes,
            "departures": [
                dep.summary(with_line=True)
                for dep in upcoming[:MAX_ATTRIBUTE_DEPARTURES]
            ],
        }
        return first


class VbbDepartureSensor(VbbBaseSensor):
    """Next departure of one line towards one destination."""

    def __init__(
        self, coordinator: VbbCoordinator, line: str, destination: str
    ) -> None:
        super().__init__(coordinator)
        self._line = line
        self._destination = destination
        self._attr_name = f"{line} {destination}"
        self._attr_unique_id = (
            f"vbb_{self._station.station_id}_{slugify(line)}_{slugify(destination)}"
        )

    def _matching(self) -> list[Departure]:
        return [
            dep
            for dep in self.coordinator.data or []
            if dep.line == self._line and dep.destination == self._destination
        ]

    def _apply(self, upcoming: list[Departure]) -> Departure | None:
        if not upcoming:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return None
        first = upcoming[0]
        self._attr_native_value = first.time
        self._attr_extra_state_attributes = {
            **self._detail_attributes(first),
            "departures": [
                dep.summary() for dep in upcoming[:MAX_ATTRIBUTE_DEPARTURES]
            ],
        }
        return first


class VbbDirectionSensor(VbbBaseSensor):
    """The n-th next departure of one line in one direction."""

    def __init__(
        self,
        coordinator: VbbCoordinator,
        line: str,
        direction: str,
        departure_index: int,
    ) -> None:
        super().__init__(coordinator)
        self._line = line
        self._direction = direction
        self._index = departure_index
        self._attr_name = f"{line} {direction} {departure_index + 1}"
        self._attr_unique_id = (
            f"vbb_{self._station.station_id}_{slugify(line)}_"
            f"{slugify(direction)}_dir_{departure_index + 1}"
        )

    def _matching(self) -> list[Departure]:
        return [
            dep
            for dep in self.coordinator.data or []
            if dep.line == self._line and dep.direction == self._direction
        ]

    def _apply(self, upcoming: list[Departure]) -> Departure | None:
        summaries = [dep.summary() for dep in upcoming[:MAX_ATTRIBUTE_DEPARTURES]]
        if len(upcoming) <= self._index:
            self._attr_native_value = None
            self._attr_extra_state_attributes = (
                {
                    "line": self._line,
                    "direction": self._direction,
                    "departure_slot": self._index + 1,
                    "station_id": self._station.station_id,
                    "departures": summaries,
                }
                if upcoming
                else {}
            )
            return upcoming[0] if upcoming else None
        selected = upcoming[self._index]
        self._attr_native_value = selected.time
        self._attr_extra_state_attributes = {
            **self._detail_attributes(selected),
            "direction": self._direction,
            "departure_slot": self._index + 1,
            "departures": summaries,
        }
        return selected
