"""Colota GPS tracking integration for Home Assistant."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from aiohttp import web
import voluptuous as vol

from homeassistant.components import webhook
from homeassistant.components.device_tracker import ATTR_BATTERY
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_WEBHOOK_ID,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow, config_validation as cv, device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ATTR_ACCURACY,
    ATTR_ALTITUDE,
    ATTR_BATTERY_STATUS,
    ATTR_BEARING,
    ATTR_DEVICE,
    ATTR_SPEED,
    ATTR_TIMESTAMP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

type ColotaConfigEntry = ConfigEntry[dict[str, Any]]

PLATFORMS = [Platform.DEVICE_TRACKER]

TRACKER_UPDATE = f"{DOMAIN}_tracker_update"

DEFAULT_ACCURACY = 200
DEFAULT_BATTERY = -1


def _id(value: str) -> str:
    """Coerce device ID by removing dashes."""
    return value.replace("-", "")


WEBHOOK_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_LATITUDE): cv.latitude,
        vol.Required(ATTR_LONGITUDE): cv.longitude,
        vol.Optional(ATTR_DEVICE, default="colota"): _id,
        vol.Optional(ATTR_ACCURACY, default=DEFAULT_ACCURACY): vol.Coerce(float),
        vol.Optional(ATTR_ALTITUDE): vol.Coerce(float),
        vol.Optional(ATTR_BATTERY, default=DEFAULT_BATTERY): vol.Coerce(float),
        vol.Optional(ATTR_BATTERY_STATUS): vol.Coerce(int),
        vol.Optional(ATTR_BEARING): vol.Coerce(float),
        vol.Optional(ATTR_SPEED): vol.Coerce(float),
        vol.Optional(ATTR_TIMESTAMP): vol.Coerce(int),
    },
    extra=vol.REMOVE_EXTRA,
)

# Map Colota's default short field names to HA attribute names
COLOTA_FIELD_MAP = {
    "lat": ATTR_LATITUDE,
    "lon": ATTR_LONGITUDE,
    "acc": ATTR_ACCURACY,
    "alt": ATTR_ALTITUDE,
    "vel": ATTR_SPEED,
    "batt": ATTR_BATTERY,
    "bs": ATTR_BATTERY_STATUS,
    "bear": ATTR_BEARING,
    "tid": ATTR_DEVICE,
    "tst": ATTR_TIMESTAMP,
}


def _normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Map Colota's default field names to the standard schema names."""
    normalized = {}
    for key, value in data.items():
        mapped_key = COLOTA_FIELD_MAP.get(key, key)
        normalized[mapped_key] = value
    return normalized


async def handle_webhook(
    hass: HomeAssistant, webhook_id: str, request: web.Request
) -> web.Response:
    """Handle incoming webhook with Colota location data."""
    try:
        raw = await request.json()
    except ValueError:
        try:
            raw = dict(await request.post())
        except (ValueError, UnicodeDecodeError) as err:
            _LOGGER.warning("Could not parse Colota webhook request: %s", err)
            return web.Response(
                text="Could not parse request body",
                status=HTTPStatus.BAD_REQUEST,
            )

    try:
        data = WEBHOOK_SCHEMA(_normalize_payload(raw))
    except vol.MultipleInvalid as error:
        _LOGGER.debug("Invalid Colota webhook payload: %s", error)
        return web.Response(
            text=error.error_message,
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    attrs = {
        ATTR_SPEED: data.get(ATTR_SPEED),
        ATTR_BEARING: data.get(ATTR_BEARING),
        ATTR_ALTITUDE: data.get(ATTR_ALTITUDE),
        ATTR_BATTERY_STATUS: data.get(ATTR_BATTERY_STATUS),
        ATTR_TIMESTAMP: data.get(ATTR_TIMESTAMP),
    }

    device = data[ATTR_DEVICE]
    _LOGGER.debug("Received Colota update for device %s", device)

    async_dispatcher_send(
        hass,
        TRACKER_UPDATE,
        device,
        (data[ATTR_LATITUDE], data[ATTR_LONGITUDE]),
        data[ATTR_BATTERY],
        data[ATTR_ACCURACY],
        attrs,
    )

    return web.Response(text=f"Setting location for {device}", status=HTTPStatus.OK)


async def async_setup_entry(
    hass: HomeAssistant, entry: ColotaConfigEntry
) -> bool:
    """Set up Colota from a config entry."""
    entry.runtime_data = {}
    webhook.async_register(
        hass, DOMAIN, "Colota", entry.data[CONF_WEBHOOK_ID], handle_webhook
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload a config entry."""
    webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ColotaConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow device removal from the UI."""
    return True


async_remove_entry = config_entry_flow.webhook_async_remove_entry
