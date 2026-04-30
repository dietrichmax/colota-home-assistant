"""Colota binary sensor platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import TRACKER_UPDATE, ColotaConfigEntry
from .const import ATTR_BATTERY_STATUS, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Mobile-side mapping (DeviceInfoHelper.kt):
#   0 = Unknown, 1 = Discharging, 2 = Charging, 3 = Full
# Treat both Charging and Full as "is_on" so the bolt indicator stays visible
# while the device is plugged in at 100%.
_CHARGING_STATES = (2, 3)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ColotaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Colota charging binary sensors from config entry."""
    tracked = entry.runtime_data["charging"]

    @callback
    def _receive_data(
        device: str,
        gps: tuple[float, float],
        battery: float,
        accuracy: float,
        attrs: dict[str, Any],
    ) -> None:
        status = attrs.get(ATTR_BATTERY_STATUS)
        if device in tracked:
            tracked[device].update_data(status)
            return

        entity = ColotaChargingSensor(device, status, tracked)
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
        entity = ColotaChargingSensor(dev_id, None, tracked)
        tracked[dev_id] = entity
        entities.append(entity)
    async_add_entities(entities)


class ColotaChargingSensor(BinarySensorEntity, RestoreEntity):
    """Charging state for a Colota device."""

    _attr_has_entity_name = True
    _attr_translation_key = "charging"
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(
        self,
        device: str,
        status: int | None,
        tracked: dict[str, ColotaChargingSensor],
    ) -> None:
        self._device_id = device
        self._tracked = tracked
        self._attr_unique_id = f"{device}_charging"
        self._attr_is_on = _coerce_charging(status)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device)},
            name=device,
            manufacturer="Colota",
        )

    @callback
    def update_data(self, status: int | None) -> None:
        self._attr_is_on = _coerce_charging(status)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._attr_is_on is not None:
            return
        if (state := await self.async_get_last_state()) is None:
            return
        if state.state == "on":
            self._attr_is_on = True
        elif state.state == "off":
            self._attr_is_on = False

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        self._tracked.pop(self._device_id, None)


def _coerce_charging(status: int | None) -> bool | None:
    if status is None or status == 0:
        return None
    return status in _CHARGING_STATES
