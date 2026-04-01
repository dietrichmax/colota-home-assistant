# Colota Home Assistant Integration

A [Home Assistant](https://www.home-assistant.io/) custom integration for [Colota](https://github.com/dietrichmax/colota) GPS tracking.

Receives location updates from the Colota mobile app via webhook and creates `device_tracker` entities in Home Assistant.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three dots menu and select **Custom repositories**
4. Add `https://github.com/dietrichmax/colota-home-assistant` as an **Integration**
5. Search for "Colota" and install it
6. Restart Home Assistant

### Manual

1. Copy the `custom_components/colota` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. In Home Assistant, go to **Settings > Devices & Services > Add Integration**
2. Search for **Colota** and add it
3. Copy the webhook URL shown after setup
4. In the Colota mobile app, go to **Settings > API Settings**
5. Select the **Home Assistant** template
6. Paste the webhook URL as the endpoint
7. No authentication is needed - the webhook URL acts as the secret

Your device will appear as a `device_tracker` entity that you can use for automations, zones and the map.

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
  "bear": 180,
  "tid": "phone",
  "tst": 1704067200
}
```

It also accepts long-form field names (`latitude`, `longitude`, `accuracy`, `altitude`, `speed`, `battery`, `bearing`, `device`).

## License

AGPL-3.0 - see [LICENSE](LICENSE) for details.
