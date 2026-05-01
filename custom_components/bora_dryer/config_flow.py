"""Config flow for the BORA dryer integration."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_HOST, DEFAULT_NAME, DOMAIN, HTTP_TIMEOUT

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)

RE_DEVICE_ID = re.compile(r"V\d+\.\d+\.\d+<br>\s*([0-9a-f]{8})<br>", re.IGNORECASE)
RE_MODEL = re.compile(r"Bora\s+(\d+)")


class BoraNotFoundError(Exception):
    """Raised when the device responds but is not a BORA."""


async def _probe(hass: HomeAssistant, host: str) -> dict[str, str]:
    """Hit /info.html and verify it looks like a BORA. Return device id + model."""
    session = async_get_clientsession(hass)
    url = f"http://{host}/info.html"
    async with session.get(
        url,
        timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT),
    ) as resp:
        resp.raise_for_status()
        body = (await resp.read()).decode("utf-8", errors="replace")

    if "Bora" not in body:
        raise BoraNotFoundError

    device_id_match = RE_DEVICE_ID.search(body)
    model_match = RE_MODEL.search(body)
    return {
        "device_id": device_id_match.group(1).lower() if device_id_match else host,
        "model": model_match.group(1) if model_match else "4xx",
    }


class BoraConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the user-initiated config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            name = user_input.get(CONF_NAME, DEFAULT_NAME).strip() or DEFAULT_NAME
            try:
                info = await _probe(self.hass, host)
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.warning("BORA probe failed for %s: %s", host, err)
                errors["base"] = "cannot_connect"
            except BoraNotFoundError:
                errors["base"] = "not_a_bora"
            else:
                await self.async_set_unique_id(info["device_id"])
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title=f"{name} {info['model']}",
                    data={CONF_HOST: host, CONF_NAME: name},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=USER_SCHEMA,
            errors=errors,
        )
