"""Tests for the Colota binary sensor platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.colota import TRACKER_UPDATE


def _attrs(status):
    return {
        "speed": None,
        "altitude": None,
        "bearing": None,
        "battery_status": status,
        "timestamp": None,
    }


async def test_charging_on_when_status_is_charging(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "phone1", (0.0, 0.0), 50.0, 10.0, _attrs(2),
    )
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.phone1_charging")
    assert state is not None
    assert state.state == "on"
    assert state.attributes["device_class"] == "battery_charging"


async def test_charging_on_when_status_is_full(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "phone2", (0.0, 0.0), 100.0, 10.0, _attrs(3),
    )
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.phone2_charging").state == "on"


async def test_charging_off_when_discharging(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "phone3", (0.0, 0.0), 50.0, 10.0, _attrs(1),
    )
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.phone3_charging").state == "off"


async def test_charging_unknown_when_status_unknown(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "phone4", (0.0, 0.0), 50.0, 10.0, _attrs(0),
    )
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.phone4_charging")
    assert state is not None
    assert state.state in ("unknown", "unavailable")


async def test_charging_flips_on_subsequent_dispatch(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "phone5", (0.0, 0.0), 50.0, 10.0, _attrs(1),
    )
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.phone5_charging").state == "off"

    async_dispatcher_send(
        hass, TRACKER_UPDATE, "phone5", (0.0, 0.0), 51.0, 10.0, _attrs(2),
    )
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.phone5_charging").state == "on"
