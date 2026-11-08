"""The Plant & Orchard Metrics integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .const import (
    CONF_ENTRY_TYPE,
    CONF_WEATHER_HUB_ENTRY_ID,
    DOMAIN,
    ENTRY_TYPE_PLANT_BLOCK,
    ENTRY_TYPE_WEATHER_HUB,
    SERVICE_LOG_IRRIGATION,
    SERVICE_RESET_SEASONAL_ACCUMULATORS,
    SERVICE_RESET_WATER_BALANCE,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall

try:
    import voluptuous as vol
    from homeassistant.const import Platform
    from homeassistant.exceptions import ConfigEntryNotReady
    from homeassistant.helpers import config_validation as cv

    HUB_PLATFORMS: list[Any] = [
        Platform.SENSOR,
        Platform.BINARY_SENSOR,
    ]

    BLOCK_PLATFORMS: list[Any] = [
        Platform.SENSOR,
        Platform.BINARY_SENSOR,
        Platform.SELECT,
        Platform.SWITCH,
        Platform.BUTTON,
        Platform.NUMBER,
    ]
except ModuleNotFoundError:  # Allows running pure-Python calculation tests outside HA
    vol = None  # type: ignore[assignment]
    HUB_PLATFORMS = []
    BLOCK_PLATFORMS = []

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Plant & Orchard Metrics from a config entry."""
    from .coordinator import PlantBlockCoordinator, WeatherHubCoordinator

    hass.data.setdefault(DOMAIN, {})
    entry_type = entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_WEATHER_HUB)

    if entry_type == ENTRY_TYPE_WEATHER_HUB:
        coordinator = WeatherHubCoordinator(hass, entry)
        await coordinator.async_setup()
        hass.data[DOMAIN][entry.entry_id] = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, HUB_PLATFORMS)
    else:
        hub_entry_id = entry.data.get(CONF_WEATHER_HUB_ENTRY_ID)
        weather_hub = hass.data[DOMAIN].get(hub_entry_id) if hub_entry_id else None
        if not isinstance(weather_hub, WeatherHubCoordinator):
            for item in hass.data[DOMAIN].values():
                if isinstance(item, WeatherHubCoordinator):
                    weather_hub = item
                    break
        if not isinstance(weather_hub, WeatherHubCoordinator):
            raise ConfigEntryNotReady("Parent Weather Hub is not loaded yet.")

        coordinator = PlantBlockCoordinator(hass, entry, weather_hub)
        await coordinator.async_setup()
        hass.data[DOMAIN][entry.entry_id] = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, BLOCK_PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _async_register_services(hass)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by reloading the config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Plant & Orchard Metrics config entry."""
    entry_type = entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_WEATHER_HUB)
    platforms = (
        HUB_PLATFORMS if entry_type == ENTRY_TYPE_WEATHER_HUB else BLOCK_PLATFORMS
    )
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator is not None:
            await coordinator.async_shutdown()
    return unload_ok


def _async_register_services(hass: HomeAssistant) -> None:
    """Register domain services once."""
    from .coordinator import PlantBlockCoordinator

    if hass.services.has_service(DOMAIN, SERVICE_LOG_IRRIGATION):
        return

    async def _handle_log_irrigation(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        amount_mm = call.data.get("amount_mm")
        liters_per_tree = call.data.get("liters_per_tree")

        for eid, coord in hass.data.get(DOMAIN, {}).items():
            if isinstance(coord, PlantBlockCoordinator) and (
                entry_id is None or eid == entry_id
            ):
                await coord.async_log_irrigation(
                    amount_mm=amount_mm, liters_per_tree=liters_per_tree
                )

    async def _handle_reset_water_balance(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        for eid, coord in hass.data.get(DOMAIN, {}).items():
            if isinstance(coord, PlantBlockCoordinator) and (
                entry_id is None or eid == entry_id
            ):
                await coord.async_reset_water_balance()

    async def _handle_reset_seasonal(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        for eid, coord in hass.data.get(DOMAIN, {}).items():
            if isinstance(coord, PlantBlockCoordinator) and (
                entry_id is None or eid == entry_id
            ):
                await coord.async_reset_seasonal_accumulators()

    hass.services.async_register(
        DOMAIN,
        SERVICE_LOG_IRRIGATION,
        _handle_log_irrigation,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Optional("amount_mm"): vol.Coerce(float),
                vol.Optional("liters_per_tree"): vol.Coerce(float),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_WATER_BALANCE,
        _handle_reset_water_balance,
        schema=vol.Schema({vol.Optional("entry_id"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_SEASONAL_ACCUMULATORS,
        _handle_reset_seasonal,
        schema=vol.Schema({vol.Optional("entry_id"): cv.string}),
    )
