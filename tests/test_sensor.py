"""Tests for the Colota sensor platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.colota import TRACKER_UPDATE


def _attrs(**overrides):
    base = {
        "speed": None,
        "altitude": None,
        "bearing": None,
        "battery_status": None,
        "timestamp": None,
    }
    base.update(overrides)
    return base


async def test_battery_sensor_created_on_dispatch(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "phone1", (0.0, 0.0), 87.0, 10.0, _attrs(),
    )
    await hass.async_block_till_done()

    state = hass.states.get("sensor.phone1_battery")
    assert state is not None
    assert state.state == "87"
    assert state.attributes["unit_of_measurement"] == "%"
    assert state.attributes["device_class"] == "battery"
    assert state.attributes["state_class"] == "measurement"


async def test_battery_sensor_updates_on_subsequent_dispatch(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "phone2", (0.0, 0.0), 50.0, 10.0, _attrs(),
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.phone2_battery").state == "50"

    async_dispatcher_send(
        hass, TRACKER_UPDATE, "phone2", (0.0, 0.0), 42.0, 10.0, _attrs(),
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.phone2_battery").state == "42"


async def test_battery_sensor_negative_becomes_unknown(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "nobatt", (0.0, 0.0), -1.0, 10.0, _attrs(),
    )
    await hass.async_block_till_done()

    state = hass.states.get("sensor.nobatt_battery")
    assert state is not None
    assert state.state in ("unknown", "unavailable")


async def test_battery_sensor_shares_device_with_tracker(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "shared", (1.0, 2.0), 60.0, 10.0, _attrs(),
    )
    await hass.async_block_till_done()

    ent_reg = hass.helpers.entity_registry.async_get(hass)
    tracker = ent_reg.async_get("device_tracker.shared")
    sensor = ent_reg.async_get("sensor.shared_battery")
    assert tracker is not None
    assert sensor is not None
    assert tracker.device_id == sensor.device_id
