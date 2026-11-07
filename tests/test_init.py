"""Behaviour tests for the coordinator-based VBB integration."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.vbb.api import VbbApiError
from custom_components.vbb.const import DOMAIN

STATION = "900320504"


def _dep(minutes, line="950", direction="S Erkner", dest="S Erkner Bhf/ZOB", product="bus", **extra):
    when = (dt_util.utcnow() + timedelta(minutes=minutes)).isoformat()
    data = {
        "tripId": f"trip-{line}-{minutes}",
        "when": when,
        "plannedWhen": when,
        "delay": 0,
        "direction": direction,
        "line": {"name": line, "product": product, "id": line.lower()},
        "destination": {"name": dest},
        "stop": {"name": "Alt Rüdersdorf, Mühle", "location": {"latitude": 52.4, "longitude": 13.8}},
    }
    data.update(extra)
    return data


def _payload():
    return {
        "departures": [
            _dep(4),
            _dep(14),
            _dep(24),
            _dep(9, direction="S Strausberg", dest="S Strausberg Bhf"),
            _dep(2, cancelled=True, when=None),
            _dep(6, line="S1", direction="Wannsee", dest="Wannsee", product="suburban"),
        ]
    }


def _entry():
    return MockConfigEntry(
        domain=DOMAIN,
        title="Alt Rüdersdorf, Mühle",
        unique_id=STATION,
        data={
            "station_id": STATION,
            "name": "Alt Rüdersdorf, Mühle",
            "duration": 120,
            "results": 100,
            "update_interval": 5,
        },
        options={"products": ["bus"]},
    )


@pytest.fixture
def api():
    with patch(
        "custom_components.vbb.coordinator.async_request_json",
        new=AsyncMock(side_effect=lambda *a, **k: _payload()),
    ) as mock:
        yield mock


async def test_single_request_for_all_sensors(hass: HomeAssistant, api, freezer: FrozenDateTimeFactory):
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    # station + 2 destinations + 2 directions * 3 slots = 9 sensors, like before
    sensors = [s for s in hass.states.async_entity_ids("sensor")]
    assert len(sensors) == 9, sensors
    assert api.await_count == 1

    # 30 s later (old behaviour: every sensor polled again) -> no new request
    freezer.tick(timedelta(seconds=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert api.await_count == 1

    # after the configured 5 minutes -> exactly one more request
    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert api.await_count == 2


async def test_unique_ids_unchanged(hass: HomeAssistant, api):
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    reg = er.async_get(hass)
    uids = {e.unique_id for e in er.async_entries_for_config_entry(reg, entry.entry_id)}
    assert f"vbb_{STATION}_station" in uids
    assert f"vbb_{STATION}_950_s_erkner_bhf_zob" in uids
    assert f"vbb_{STATION}_950_s_erkner_dir_1" in uids
    assert f"vbb_{STATION}_950_s_strausberg_dir_3" in uids
    # product filter: S1 (suburban) must not create sensors
    assert not any("s1" in u for u in uids)


async def test_cancelled_skipped_and_rollover(hass: HomeAssistant, api, freezer: FrozenDateTimeFactory):
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    station = hass.states.get("sensor.alt_rudersdorf_muhle")
    first = dt_util.parse_datetime(station.state)
    # cancelled departure in 2 min is ignored -> first is the one in 4 min
    assert round((first - dt_util.utcnow()).total_seconds() / 60) == 4
    assert station.attributes["delay"] == 0
    assert len(station.attributes["departures"]) <= 10

    slot1 = hass.states.get("sensor.950_s_erkner_1").state
    # departure leaves -> sensor switches to the next one without an API call
    freezer.tick(timedelta(minutes=4, seconds=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert api.await_count == 1
    assert hass.states.get("sensor.950_s_erkner_1").state != slot1
    new_first = dt_util.parse_datetime(hass.states.get("sensor.alt_rudersdorf_muhle").state)
    assert round((new_first - dt_util.utcnow()).total_seconds() / 60) == 5  # the 9-min bus


async def test_setup_retry_when_api_down(hass: HomeAssistant):
    entry = _entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.vbb.coordinator.async_request_json",
        new=AsyncMock(side_effect=VbbApiError("down")),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_keeps_data_on_temporary_error(hass: HomeAssistant, api, freezer: FrozenDateTimeFactory):
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    api.side_effect = VbbApiError("blip")
    freezer.tick(timedelta(minutes=5, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.alt_rudersdorf_muhle").state != "unavailable"


async def test_switch_reloads_once_and_unload(hass: HomeAssistant, api):
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    calls = api.await_count
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.suburban"}, blocking=True)
    await hass.async_block_till_done()
    assert "suburban" in entry.options["products"]
    assert api.await_count == calls + 1  # exactly one reload
    assert any("s1" in (e.unique_id) for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id))
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_options_flow(hass: HomeAssistant, api):
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"update_interval": 2, "duration": 60, "results": 50, "products": ["bus"]},
    )
    await hass.async_block_till_done()
    assert entry.options["update_interval"] == 2
    assert entry.runtime_data.update_interval == timedelta(minutes=2)
