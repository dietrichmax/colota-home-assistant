"""Colota sensor platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import TRACKER_UPDATE, ColotaConfigEntry
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ColotaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Colota battery sensors from config entry."""
    tracked = entry.runtime_data["battery"]

    @callback
    def _receive_data(
        device: str,
        gps: tuple[float, float],
        battery: float,
        accuracy: float,
        attrs: dict[str, Any],
    ) -> None:
        if device in tracked:
            tracked[device].update_data(battery)
            return

        entity = ColotaBatterySensor(device, battery, tracked)
        tracked[device] = entity
        async_add_entities([entity])

    entry.async_on_unload(
        async_dispatcher_connect(hass, TRACKER_UPDATE, _receive_data)
    )

    dev_reg = dr.async_get(hass)
    dev_ids = {
        identifier[1]
        for device in dev_reg.devices.get_devices_for_config_entry_id(entry.entry_id)
        for identifier in device.identifiers
    }
    if not dev_ids:
        return

    entities = []
    for dev_id in dev_ids:
        entity = ColotaBatterySensor(dev_id, None, tracked)
        tracked[dev_id] = entity
        entities.append(entity)
    async_add_entities(entities)


class ColotaBatterySensor(SensorEntity, RestoreEntity):
    """Battery level sensor for a Colota device."""

    _attr_has_entity_name = True
    _attr_translation_key = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        device: str,
        battery: float | None,
        tracked: dict[str, ColotaBatterySensor],
    ) -> None:
        self._device_id = device
        self._tracked = tracked
        self._attr_unique_id = f"{device}_battery"
        self._attr_native_value = _coerce_battery(battery)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device)},
            name=device,
            manufacturer="Colota",
        )

    @callback
    def update_data(self, battery: float | None) -> None:
        self._attr_native_value = _coerce_battery(battery)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._attr_native_value is not None:
            return
        if (state := await self.async_get_last_state()) is None:
            return
        try:
            self._attr_native_value = int(state.state)
        except (TypeError, ValueError):
            self._attr_native_value = None

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        self._tracked.pop(self._device_id, None)


def _coerce_battery(battery: float | None) -> int | None:
    if battery is None or battery < 0:
        return None
    return int(battery)
