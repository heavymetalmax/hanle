"""Config flow for NoLongerEvil integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import NLEApiClient, NLEAuthError, NLEConnectionError
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): NumberSelector(
            NumberSelectorConfig(min=30, max=600, step=10, mode=NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
    }
)


class NLEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NoLongerEvil."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            base_url = user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL)

            try:
                session = aiohttp_client.async_get_clientsession(self.hass)
                client = NLEApiClient(api_key, session, base_url)
                devices = await client.list_devices()
            except NLEAuthError:
                errors["base"] = "invalid_auth"
            except NLEConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during NLE setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(api_key[:16])
                self._abort_if_unique_id_configured()
                device_names = ", ".join(
                    d.get("label") or d.get("name") or d.get("id", "?")
                    for d in devices
                )
                return self.async_create_entry(
                    title=f"NoLongerEvil ({device_names or 'Nest'})",
                    data={CONF_API_KEY: api_key, CONF_BASE_URL: base_url},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NLEOptionsFlow:
        return NLEOptionsFlow(config_entry)


class NLEOptionsFlow(config_entries.OptionsFlow):
    """Handle options for NoLongerEvil."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        current_url = self._config_entry.options.get(
            CONF_BASE_URL,
            self._config_entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): NumberSelector(
                    NumberSelectorConfig(min=30, max=600, step=10, mode=NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_BASE_URL, default=current_url): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.URL)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
