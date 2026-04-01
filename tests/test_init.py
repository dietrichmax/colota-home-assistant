"""Tests for Colota integration setup and webhook handling."""

from __future__ import annotations

from http import HTTPStatus

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.colota import TRACKER_UPDATE

WEBHOOK_URL = "/api/webhook/test-webhook-id"


async def test_setup_entry(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Test successful setup of a config entry."""
    assert setup_integration.state is ConfigEntryState.LOADED
    assert setup_integration.runtime_data == {}


async def test_unload_entry(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Test unloading a config entry."""
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert setup_integration.state is ConfigEntryState.NOT_LOADED


async def test_webhook_valid_payload(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """Test webhook with a valid location payload."""
    client = await hass_client_no_auth()

    signals: list[tuple] = []

    @callback
    def _track(*args: object) -> None:
        signals.append(args)

    async_dispatcher_connect(hass, TRACKER_UPDATE, _track)

    resp = await client.post(
        WEBHOOK_URL,
        json={
            "latitude": 48.8566,
            "longitude": 2.3522,
            "device": "test-phone",
            "battery": 85,
            "accuracy": 10,
        },
    )

    assert resp.status == HTTPStatus.OK
    text = await resp.text()
    assert "testphone" in text

    assert len(signals) == 1
    device, gps, battery, accuracy, attrs = signals[0]
    assert device == "testphone"
    assert gps == (48.8566, 2.3522)
    assert battery == 85.0
    assert accuracy == 10.0


async def test_webhook_short_field_names(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """Test webhook with Colota's short field names."""
    client = await hass_client_no_auth()

    signals: list[tuple] = []

    @callback
    def _track(*args: object) -> None:
        signals.append(args)

    async_dispatcher_connect(hass, TRACKER_UPDATE, _track)

    resp = await client.post(
        WEBHOOK_URL,
        json={
            "lat": 52.5200,
            "lon": 13.4050,
            "tid": "my-device",
            "batt": 50,
            "acc": 15,
            "vel": 3.5,
            "alt": 120.0,
            "bear": 180.0,
        },
    )

    assert resp.status == HTTPStatus.OK

    assert len(signals) == 1
    device, gps, battery, accuracy, attrs = signals[0]
    assert device == "mydevice"
    assert gps == (52.5200, 13.4050)
    assert battery == 50.0
    assert accuracy == 15.0
    assert attrs["speed"] == 3.5
    assert attrs["altitude"] == 120.0
    assert attrs["bearing"] == 180.0


async def test_webhook_defaults(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """Test webhook applies correct defaults for optional fields."""
    client = await hass_client_no_auth()

    signals: list[tuple] = []

    @callback
    def _track(*args: object) -> None:
        signals.append(args)

    async_dispatcher_connect(hass, TRACKER_UPDATE, _track)

    resp = await client.post(
        WEBHOOK_URL,
        json={"latitude": 0.0, "longitude": 0.0},
    )

    assert resp.status == HTTPStatus.OK

    device, _, battery, accuracy, _ = signals[0]
    assert device == "colota"
    assert battery == -1.0
    assert accuracy == 200.0


async def test_webhook_missing_required_fields(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """Test webhook returns 422 when required fields are missing."""
    client = await hass_client_no_auth()

    resp = await client.post(
        WEBHOOK_URL,
        json={"device": "test"},
    )

    assert resp.status == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_webhook_extra_fields_stripped(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """Test webhook strips unexpected extra fields."""
    client = await hass_client_no_auth()

    signals: list[tuple] = []

    @callback
    def _track(*args: object) -> None:
        signals.append(args)

    async_dispatcher_connect(hass, TRACKER_UPDATE, _track)

    resp = await client.post(
        WEBHOOK_URL,
        json={
            "latitude": 1.0,
            "longitude": 2.0,
            "unknown_field": "should be removed",
        },
    )

    assert resp.status == HTTPStatus.OK
    assert len(signals) == 1
