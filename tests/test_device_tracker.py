"""Tests for the Colota device tracker platform."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.colota import TRACKER_UPDATE
from custom_components.colota.const import DOMAIN


async def test_new_device_creates_entity(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Test that a new device dispatched via webhook creates an entity."""
    async_dispatcher_send(
        hass,
        TRACKER_UPDATE,
        "phone1",
        (48.8566, 2.3522),
        85.0,
        10.0,
        {"speed": 1.5, "altitude": 100.0, "bearing": None, "battery_status": None, "timestamp": None},
    )
    await hass.async_block_till_done()

    state = hass.states.get("device_tracker.phone1")
    assert state is not None
    assert state.attributes["latitude"] == 48.8566
    assert state.attributes["longitude"] == 2.3522
    assert state.attributes["gps_accuracy"] == 10.0
    assert state.attributes["speed"] == 1.5


async def test_device_update(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Test that subsequent dispatches update the existing entity."""
    attrs = {"speed": None, "altitude": None, "bearing": None, "battery_status": None, "timestamp": None}

    # First dispatch creates the entity
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "phone2", (1.0, 2.0), 50.0, 20.0, attrs,
    )
    await hass.async_block_till_done()

    state = hass.states.get("device_tracker.phone2")
    assert state is not None
    assert state.attributes["latitude"] == 1.0

    # Second dispatch updates it
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "phone2", (3.0, 4.0), 60.0, 5.0, {**attrs, "speed": 10.0},
    )
    await hass.async_block_till_done()

    state = hass.states.get("device_tracker.phone2")
    assert state.attributes["latitude"] == 3.0
    assert state.attributes["longitude"] == 4.0
    assert state.attributes["gps_accuracy"] == 5.0
    assert state.attributes["speed"] == 10.0


async def test_multiple_devices(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Test tracking multiple devices simultaneously."""
    attrs = {"speed": None, "altitude": None, "bearing": None, "battery_status": None, "timestamp": None}

    async_dispatcher_send(
        hass, TRACKER_UPDATE, "device_a", (10.0, 20.0), 80.0, 5.0, attrs,
    )
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "device_b", (30.0, 40.0), 90.0, 8.0, attrs,
    )
    await hass.async_block_till_done()

    state_a = hass.states.get("device_tracker.device_a")
    state_b = hass.states.get("device_tracker.device_b")
    assert state_a is not None
    assert state_b is not None
    assert state_a.attributes["latitude"] == 10.0
    assert state_b.attributes["latitude"] == 30.0


async def test_battery_level_negative_returns_none(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Test that negative battery values are reported as None."""
    attrs = {"speed": None, "altitude": None, "bearing": None, "battery_status": None, "timestamp": None}

    async_dispatcher_send(
        hass, TRACKER_UPDATE, "nobatt", (1.0, 2.0), -1.0, 10.0, attrs,
    )
    await hass.async_block_till_done()

    state = hass.states.get("device_tracker.nobatt")
    assert state is not None
    assert state.attributes.get("battery_level") is None


async def test_entity_removal_cleans_tracked(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Test that removing an entity allows the device to be re-registered."""
    attrs = {"speed": None, "altitude": None, "bearing": None, "battery_status": None, "timestamp": None}

    # Create entity
    async_dispatcher_send(
        hass, TRACKER_UPDATE, "removable", (1.0, 2.0), 50.0, 10.0, attrs,
    )
    await hass.async_block_till_done()

    assert "removable" in setup_integration.runtime_data

    # Remove the entity via the entity registry
    entity_registry = hass.helpers.entity_registry.async_get(hass)
    entity_entry = entity_registry.async_get("device_tracker.removable")
    if entity_entry:
        entity_registry.async_remove(entity_entry.entity_id)
        await hass.async_block_till_done()

        # After removal, the device should no longer be in the tracked dict
        assert "removable" not in setup_integration.runtime_data

        # A new dispatch should re-create the entity
        async_dispatcher_send(
            hass, TRACKER_UPDATE, "removable", (5.0, 6.0), 70.0, 5.0, attrs,
        )
        await hass.async_block_till_done()

        state = hass.states.get("device_tracker.removable")
        assert state is not None
        assert state.attributes["latitude"] == 5.0


async def test_device_info(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Test that device info is correctly set."""
    attrs = {"speed": None, "altitude": None, "bearing": None, "battery_status": None, "timestamp": None}

    async_dispatcher_send(
        hass, TRACKER_UPDATE, "myphone", (1.0, 2.0), 50.0, 10.0, attrs,
    )
    await hass.async_block_till_done()

    dev_reg = hass.helpers.device_registry.async_get(hass)
    device = dev_reg.async_get_device(identifiers={(DOMAIN, "myphone")})
    assert device is not None
    assert device.name == "myphone"
    assert device.manufacturer == "Colota"
