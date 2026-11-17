# Colota Home Assistant Integration

[![HACS Default](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/default)
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)

A [Home Assistant](https://www.home-assistant.io/) custom integration for [Colota](https://github.com/dietrichmax/colota) GPS tracking.

Receives location updates from the Colota mobile app via webhook and creates `device_tracker`, `sensor` and `binary_sensor` entities in Home Assistant.

## Installation

### HACS (recommended)

Colota is in the HACS default store, so no custom repository is needed.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dietrichmax&repository=colota-home-assistant&category=integration)

1. Open HACS in Home Assistant
2. Search for "Colota" and install it
3. Restart Home Assistant

### Manual

1. Copy the `custom_components/colota` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. In Home Assistant, go to **Settings > Devices & Services > Add Integration**
2. Search for **Colota** and add it
3. Copy the webhook URL shown after setup
4. In the Colota mobile app, go to **Settings > Connection**
5. Paste the webhook URL as the **Server endpoint**
6. No authentication is needed - the webhook URL acts as the secret

## Entities

Each device creates three entities:

| Entity | Description |
| --- | --- |
| `device_tracker` | Location, for automations, zones and the map |
| `sensor` | Battery level in percent, from the `batt` field |
| `binary_sensor` | Charging state, from the `bs` field |

## Payload

The integration accepts Colota's default payload format:

```json
{
  "lat": 51.5074,
  "lon": -0.1278,
  "acc": 15,
  "alt": 20,
  "vel": 1.5,
  "batt": 85,
  "bs": 2,
  "bear": 180,
  "tid": "phone",
  "tst": 1704067200
}
```

`bs` is the battery status: `0` unknown, `1` discharging, `2` charging, `3` full. The charging sensor is on for both `2` and `3`, so it stays on while the device is plugged in at 100%.

It also accepts long-form field names (`latitude`, `longitude`, `accuracy`, `altitude`, `speed`, `battery`, `battery_status`, `bearing`, `device`, `timestamp`).

## Geofence events

With **Send enter and leave events** turned on, Colota also posts an event each time the phone enters or leaves one of its geofences. The integration fires these on the event bus as `colota_geofence` and leaves the device tracker alone, which keeps following the location points. Zones keep working as before.

| Field | Value |
| --- | --- |
| `device` | Device ID, the same one the tracker uses |
| `event` | `enter` or `leave` |
| `geofence` | Name of the geofence in Colota |
| `timestamp` | Unix time of the fix the event happened at |

Colota counts a geofence as left only after two fixes in a row lie outside its radius plus their accuracy, so a trigger on this event fires less often on GPS jitter than one on zone state. It also works for geofences that don't exist as zones in Home Assistant.

```yaml
triggers:
  - trigger: event
    event_type: colota_geofence
    event_data:
      device: phone
      event: leave
      geofence: Home
actions:
  - action: notify.notify
    data:
      message: "Left Home"
```

## License

AGPL-3.0 - see [LICENSE](LICENSE) for details.
