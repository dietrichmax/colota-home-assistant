"""Config flow for Colota."""

from homeassistant.helpers import config_entry_flow

from .const import DOMAIN

config_entry_flow.register_webhook_flow(
    DOMAIN,
    "Colota Webhook",
    {"docs_url": "https://colota.app/docs/integrations/home-assistant"},
)
