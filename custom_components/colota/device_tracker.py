"""Colota device tracker platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_GPS_ACCURACY,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import TRACKER_UPDATE, ColotaConfigEntry
from .const import (
    ATTR_ALTITUDE,
    ATTR_BATTERY_STATUS,
    ATTR_BEARING,
    ATTR_SPEED,
    ATTR_TIMESTAMP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ColotaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Colota device tracker from config entry."""
    tracked = entry.runtime_data["tracker"]

    @callback
    def _receive_data(
        device: str,
        gps: tuple[float, float],
        battery: float,
        accuracy: float,
        attrs: dict[str, Any],
    ) -> None:
        """Receive location data from dispatcher."""
        if device in tracked:
            tracked[device].update_data(gps, battery, accuracy, attrs)
            return

        _LOGGER.debug("Registering new Colota device: %s", device)
        entity = ColotaEntity(device, gps, battery, accuracy, attrs, tracked)
        tracked[device] = entity
        async_add_entities([entity])

    entry.async_on_unload(
        async_dispatcher_connect(hass, TRACKER_UPDATE, _receive_data)
    )

    # Restore previously known devices from the device registry
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
        entity = ColotaEntity(dev_id, None, None, None, None, tracked)
        tracked[dev_id] = entity
        entities.append(entity)
    async_add_entities(entities)


class ColotaEntity(TrackerEntity, RestoreEntity):
    """Represent a Colota tracked device."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        device: str,
        location: tuple[float, float] | None,
        battery: float | None,
        accuracy: float | None,
        attributes: dict[str, Any] | None,
        tracked: dict[str, ColotaEntity],
    ) -> None:
        """Initialize the entity."""
        self._device_id = device
        self._tracked = tracked
        self._attr_unique_id = device
        self._attr_location_accuracy = accuracy or 0
        self._attr_extra_state_attributes = attributes or {}
        self._battery = battery
        if location:
            self._attr_latitude = location[0]
            self._attr_longitude = location[1]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device)},
            name=device,
            manufacturer="Colota",
        )

    @property
    def battery_level(self) -> int | None:
        """Return battery value of the device."""
        if self._battery is None or self._battery < 0:
            return None
        return int(self._battery)

    @callback
    def update_data(
        self,
        location: tuple[float, float],
        battery: float,
        accuracy: float,
        attributes: dict[str, Any],
    ) -> None:
        """Update entity with new data from webhook."""
        self._attr_latitude = location[0]
        self._attr_longitude = location[1]
        self._battery = battery
        self._attr_location_accuracy = accuracy
        self._attr_extra_state_attributes.update(attributes)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore state if available."""
        await super().async_added_to_hass()

        # Don't restore if we were created with data
        if self.latitude is not None:
            return

        if (state := await self.async_get_last_state()) is None:
            self._attr_latitude = None
            self._attr_longitude = None
            self._attr_location_accuracy = 0
            self._attr_extra_state_attributes = {
                ATTR_ALTITUDE: None,
                ATTR_BEARING: None,
                ATTR_SPEED: None,
                ATTR_BATTERY_STATUS: None,
                ATTR_TIMESTAMP: None,
            }
            self._battery = None
            return

        attr = state.attributes
        self._attr_latitude = attr.get(ATTR_LATITUDE)
        self._attr_longitude = attr.get(ATTR_LONGITUDE)
        self._attr_location_accuracy = attr.get(ATTR_GPS_ACCURACY, 0)
        self._attr_extra_state_attributes = {
            ATTR_ALTITUDE: attr.get(ATTR_ALTITUDE),
            ATTR_BEARING: attr.get(ATTR_BEARING),
            ATTR_SPEED: attr.get(ATTR_SPEED),
            ATTR_BATTERY_STATUS: attr.get(ATTR_BATTERY_STATUS),
            ATTR_TIMESTAMP: attr.get(ATTR_TIMESTAMP),
        }
        self._battery = attr.get(ATTR_BATTERY_LEVEL)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up tracked reference so the device can be re-registered."""
        await super().async_will_remove_from_hass()
        self._tracked.pop(self._device_id, None)
