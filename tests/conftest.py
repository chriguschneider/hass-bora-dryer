"""Shared pytest fixtures.

``enable_custom_integrations`` (autouse) makes every test that requests the
``hass`` fixture load the custom component from the repo tree. Tests that
do not use ``hass`` (metadata and changelog tests) are unaffected.

The device never answers for real: ``aioclient_mock`` (from
pytest-homeassistant-custom-component) replaces the shared aiohttp session,
and ``mock_device`` registers the fixture pages under the test host. See
tests/README.md for where the fixtures come from.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import aiohttp
import pytest
from homeassistant.const import CONF_HOST, CONF_NAME
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.bora_dryer.const import DOMAIN

FIXTURES = Path(__file__).parent / "fixtures"
HOST = "192.0.2.10"  # TEST-NET-1, never routable
# Values the fixtures carry (tests/fixtures/info.html).
DEVICE_ID = "0a1b2c3d"
MODEL = "410"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def register_device(
    aioclient_mock: AiohttpClientMocker,
    host: str = HOST,
    *,
    status: str | None = None,
    info: str | None = None,
) -> None:
    """Let ``host`` answer with the fixture pages (or the given bodies)."""
    aioclient_mock.get(
        f"http://{host}/status.html",
        text=status if status is not None else load_fixture("status.html"),
    )
    aioclient_mock.get(
        f"http://{host}/info.html",
        text=info if info is not None else load_fixture("info.html"),
    )


def register_offline(aioclient_mock: AiohttpClientMocker, host: str = HOST) -> None:
    """Nothing answers on ``host``: every page raises a connection error."""
    for page in ("status.html", "info.html"):
        aioclient_mock.get(
            f"http://{host}/{page}", exc=aiohttp.ClientConnectionError("off")
        )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ from this repo in every hass test."""
    return


@pytest.fixture
def config_entry(hass) -> MockConfigEntry:
    """A config entry as the config flow creates it, added but not set up."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"BORA {MODEL}",
        unique_id=DEVICE_ID,
        data={CONF_HOST: HOST, CONF_NAME: "BORA"},
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_device(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """The device at HOST is on and answers with the fixture pages."""
    register_device(aioclient_mock)
    return aioclient_mock


@pytest.fixture
def switch_device(
    aioclient_mock: AiohttpClientMocker,
) -> Callable[..., None]:
    """Switch the device at HOST on (default pages or given bodies) or off."""

    def _switch(on: bool, **pages: str) -> None:
        aioclient_mock.clear_requests()
        if on:
            register_device(aioclient_mock, **pages)
        else:
            register_offline(aioclient_mock)

    return _switch
