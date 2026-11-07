"""VBB departures integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DURATION,
    CONF_PRODUCTS,
    CONF_RESULTS,
    CONF_STATION_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_DURATION,
    DEFAULT_PRODUCTS,
    DEFAULT_RESULTS,
    DEFAULT_UPDATE_INTERVAL,
)
from .coordinator import StationConfig, VbbCoordinator

PLATFORMS = [Platform.SENSOR, Platform.SWITCH]

type VbbConfigEntry = ConfigEntry[VbbCoordinator]


def station_config_from_entry(entry: ConfigEntry) -> StationConfig:
    """Build the station configuration; options override the initial data."""

    def _get(key: str, default):
        return entry.options.get(key, entry.data.get(key, default))

    return StationConfig(
        station_id=entry.data[CONF_STATION_ID],
        name=entry.data[CONF_NAME],
        duration=int(_get(CONF_DURATION, DEFAULT_DURATION)),
        results=int(_get(CONF_RESULTS, DEFAULT_RESULTS)),
        products=frozenset(_get(CONF_PRODUCTS, DEFAULT_PRODUCTS)),
        update_interval=int(_get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)),
    )


async def async_setup_entry(hass: HomeAssistant, entry: VbbConfigEntry) -> bool:
    """Set up VBB from a config entry."""
    coordinator = VbbCoordinator(hass, station_config_from_entry(entry), entry)
    # Raises ConfigEntryNotReady on failure, so HA retries setup with back-off.
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: VbbConfigEntry) -> None:
    """Reload the entry so changed options (products, interval) take effect."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: VbbConfigEntry) -> bool:
    """Unload a VBB config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
