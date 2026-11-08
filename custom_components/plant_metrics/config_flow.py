"""Config flow and Options flow for Plant & Orchard Metrics."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_AVAILABLE_WATER_CAPACITY_MM_M,
    CONF_BLOCK_NAME,
    CONF_CANOPY_AREA_M2,
    CONF_CANOPY_TEMP_ENTITY,
    CONF_ELEVATION,
    CONF_ENTRY_TYPE,
    CONF_GDD_BASE_TEMP,
    CONF_GDD_UPPER_TEMP,
    CONF_HUMIDITY_ENTITY,
    CONF_IRRIGATION_EFFICIENCY,
    CONF_PLANT_PROFILE,
    CONF_PLANTS_COUNT,
    CONF_PRESSURE_ENTITY,
    CONF_PRIMARY_CHILL_TARGET,
    CONF_RAIN_DAILY_ENTITY,
    CONF_RAIN_RATE_ENTITY,
    CONF_ROOT_DEPTH_MM,
    CONF_SECONDARY_CHILL_TARGET,
    CONF_SITE_NAME,
    CONF_SOIL_MOISTURE_ENTITIES,
    CONF_SOIL_TEMP_ENTITY,
    CONF_SOLAR_RAD_ENTITY,
    CONF_TEMP_ENTITY,
    CONF_UV_ENTITY,
    CONF_WEATHER_HUB_ENTRY_ID,
    CONF_WIND_GUST_ENTITY,
    CONF_WIND_SPEED_ENTITY,
    DEFAULT_AWC_MM_M,
    DEFAULT_ELEVATION,
    DEFAULT_IRRIGATION_EFFICIENCY,
    DEFAULT_PLANTS_COUNT,
    DOMAIN,
    ENTRY_TYPE_PLANT_BLOCK,
    ENTRY_TYPE_WEATHER_HUB,
)
from .plants import PLANT_PROFILES, get_plant_profile


def _detect_weather_station_defaults(hass: HomeAssistant) -> dict[str, str]:
    """Auto-detect standard weather station entities if present in Home Assistant."""
    candidates: dict[str, list[str]] = {
        CONF_TEMP_ENTITY: [
            "sensor.ecowitt_outdoor_temperature",
            "sensor.outdoor_temperature",
        ],
        CONF_HUMIDITY_ENTITY: [
            "sensor.ecowitt_humidity",
            "sensor.outdoor_humidity",
        ],
        CONF_WIND_SPEED_ENTITY: [
            "sensor.ecowitt_wind_speed",
            "sensor.wind_speed",
        ],
        CONF_WIND_GUST_ENTITY: [
            "sensor.ecowitt_wind_gust",
            "sensor.wind_gust",
        ],
        CONF_SOLAR_RAD_ENTITY: [
            "sensor.ecowitt_solar_radiation",
            "sensor.solar_radiation",
        ],
        CONF_PRESSURE_ENTITY: [
            "sensor.ecowitt_relative_pressure",
            "sensor.ecowitt_absolute_pressure",
            "sensor.barometric_pressure",
        ],
        CONF_RAIN_RATE_ENTITY: [
            "sensor.ecowitt_rain_rate",
            "sensor.rain_rate",
        ],
        CONF_RAIN_DAILY_ENTITY: [
            "sensor.ecowitt_daily_rain",
            "sensor.daily_rain",
        ],
        CONF_UV_ENTITY: [
            "sensor.ecowitt_uv_index",
            "sensor.uv_index",
        ],
    }
    found: dict[str, str] = {}
    for conf_key, entity_list in candidates.items():
        for entity_id in entity_list:
            if hass.states.get(entity_id) is not None:
                found[conf_key] = entity_id
                break
    return found


def _build_weather_hub_schema(
    defaults: dict[str, Any], default_elevation: float
) -> vol.Schema:
    """Build voluptuous schema for configuring a Weather Station Hub."""
    fields: dict[Any, Any] = {
        vol.Required(
            CONF_SITE_NAME,
            default=defaults.get(CONF_SITE_NAME, "Weather Station Hub"),
        ): selector.TextSelector(),
        vol.Required(
            CONF_TEMP_ENTITY,
            default=defaults.get(CONF_TEMP_ENTITY, vol.UNDEFINED),
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Required(
            CONF_HUMIDITY_ENTITY,
            default=defaults.get(CONF_HUMIDITY_ENTITY, vol.UNDEFINED),
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(
            CONF_WIND_SPEED_ENTITY,
            description={"suggested_value": defaults.get(CONF_WIND_SPEED_ENTITY)},
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(
            CONF_WIND_GUST_ENTITY,
            description={"suggested_value": defaults.get(CONF_WIND_GUST_ENTITY)},
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(
            CONF_SOLAR_RAD_ENTITY,
            description={"suggested_value": defaults.get(CONF_SOLAR_RAD_ENTITY)},
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(
            CONF_PRESSURE_ENTITY,
            description={"suggested_value": defaults.get(CONF_PRESSURE_ENTITY)},
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(
            CONF_RAIN_RATE_ENTITY,
            description={"suggested_value": defaults.get(CONF_RAIN_RATE_ENTITY)},
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(
            CONF_RAIN_DAILY_ENTITY,
            description={"suggested_value": defaults.get(CONF_RAIN_DAILY_ENTITY)},
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(
            CONF_UV_ENTITY,
            description={"suggested_value": defaults.get(CONF_UV_ENTITY)},
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Required(
            CONF_ELEVATION,
            default=defaults.get(CONF_ELEVATION, default_elevation),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-50,
                max=4000,
                step=1,
                unit_of_measurement="m",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
    }
    return vol.Schema(fields)


def _build_block_details_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build voluptuous schema for Plant Block agronomic & sensor parameters."""
    profile_key = defaults.get(CONF_PLANT_PROFILE, "hazelnut_tonda_di_giffoni")
    profile = get_plant_profile(profile_key)

    fields: dict[Any, Any] = {
        vol.Required(
            CONF_PRIMARY_CHILL_TARGET,
            default=defaults.get(
                CONF_PRIMARY_CHILL_TARGET, profile.primary_chill_units
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=50,
                max=1800,
                step=10,
                unit_of_measurement="CU",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_SECONDARY_CHILL_TARGET,
            default=defaults.get(
                CONF_SECONDARY_CHILL_TARGET, profile.secondary_chill_units
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=50,
                max=1800,
                step=10,
                unit_of_measurement="CU",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_GDD_BASE_TEMP,
            default=defaults.get(CONF_GDD_BASE_TEMP, profile.gdd_base_c),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.0,
                max=15.0,
                step=0.5,
                unit_of_measurement="°C",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_GDD_UPPER_TEMP,
            default=defaults.get(CONF_GDD_UPPER_TEMP, profile.gdd_upper_c),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=22.0,
                max=40.0,
                step=0.5,
                unit_of_measurement="°C",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_CANOPY_AREA_M2,
            default=defaults.get(
                CONF_CANOPY_AREA_M2, profile.default_canopy_area_m2
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.01,
                max=60.0,
                step=0.05,
                unit_of_measurement="m²",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_PLANTS_COUNT,
            default=defaults.get(CONF_PLANTS_COUNT, DEFAULT_PLANTS_COUNT),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=100000,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_ROOT_DEPTH_MM,
            default=defaults.get(
                CONF_ROOT_DEPTH_MM, profile.default_root_depth_mm
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=50,
                max=1500,
                step=10,
                unit_of_measurement="mm",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_AVAILABLE_WATER_CAPACITY_MM_M,
            default=defaults.get(
                CONF_AVAILABLE_WATER_CAPACITY_MM_M, DEFAULT_AWC_MM_M
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=50,
                max=350,
                step=5,
                unit_of_measurement="mm/m",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_IRRIGATION_EFFICIENCY,
            default=defaults.get(
                CONF_IRRIGATION_EFFICIENCY, DEFAULT_IRRIGATION_EFFICIENCY
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.4,
                max=1.0,
                step=0.05,
                mode=selector.NumberSelectorMode.SLIDER,
            )
        ),
        vol.Optional(
            CONF_SOIL_MOISTURE_ENTITIES,
            default=defaults.get(CONF_SOIL_MOISTURE_ENTITIES, []),
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", multiple=True)
        ),
        vol.Optional(
            CONF_SOIL_TEMP_ENTITY,
            description={"suggested_value": defaults.get(CONF_SOIL_TEMP_ENTITY)},
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(
            CONF_CANOPY_TEMP_ENTITY,
            description={"suggested_value": defaults.get(CONF_CANOPY_TEMP_ENTITY)},
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
    }
    return vol.Schema(fields)


class PlantMetricsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Plant & Orchard Metrics."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow state."""
        self._block_base_data: dict[str, Any] = {}

    def _get_weather_hub_entries(self) -> list[config_entries.ConfigEntry]:
        """Return existing Weather Hub config entries."""
        return [
            entry
            for entry in self._async_current_entries()
            if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_WEATHER_HUB
        ]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Initial step: if a Weather Hub exists, show menu; otherwise configure Weather Hub first."""
        hubs = self._get_weather_hub_entries()
        if not hubs:
            return await self.async_step_weather_hub()

        return self.async_show_menu(
            step_id="user",
            menu_options=["plant_block", "weather_hub"],
        )

    async def async_step_weather_hub(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure a Weather Station Hub."""
        default_elev = (
            float(self.hass.config.elevation)
            if self.hass and self.hass.config.elevation is not None
            else DEFAULT_ELEVATION
        )
        if user_input is not None:
            data = {
                **user_input,
                CONF_ENTRY_TYPE: ENTRY_TYPE_WEATHER_HUB,
            }
            return self.async_create_entry(
                title=user_input[CONF_SITE_NAME],
                data=data,
            )

        return self.async_show_form(
            step_id="weather_hub",
            data_schema=_build_weather_hub_schema(
                _detect_weather_station_defaults(self.hass), default_elev
            ),
        )

    async def async_step_plant_block(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1 of adding a Plant / Orchard Block: name, weather hub, and plant profile selection."""
        hubs = self._get_weather_hub_entries()
        if not hubs:
            return await self.async_step_weather_hub()

        if user_input is not None:
            self._block_base_data = user_input
            return await self.async_step_plant_block_details()

        hub_options = [
            selector.SelectOptionDict(value=entry.entry_id, label=entry.title)
            for entry in hubs
        ]
        profile_options = [
            selector.SelectOptionDict(value=key, label=profile.name)
            for key, profile in PLANT_PROFILES.items()
        ]

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BLOCK_NAME, default="Orchard Block"
                ): selector.TextSelector(),
                vol.Required(
                    CONF_WEATHER_HUB_ENTRY_ID, default=hubs[0].entry_id
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=hub_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_PLANT_PROFILE, default="hazelnut_tonda_di_giffoni"
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=profile_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="plant_block",
            data_schema=schema,
        )

    async def async_step_plant_block_details(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2 of adding a Plant / Orchard Block: chill, GDD, canopy/root-zone, and soil sensors."""
        if user_input is not None:
            full_data = {
                **self._block_base_data,
                **user_input,
                CONF_ENTRY_TYPE: ENTRY_TYPE_PLANT_BLOCK,
            }
            return self.async_create_entry(
                title=self._block_base_data[CONF_BLOCK_NAME],
                data=full_data,
            )

        return self.async_show_form(
            step_id="plant_block_details",
            data_schema=_build_block_details_schema(self._block_base_data),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow handler."""
        return PlantMetricsOptionsFlowHandler(config_entry)


class PlantMetricsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options updates for Weather Hub or Plant Block entries."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        merged = {**self._entry.data, **self._entry.options}
        entry_type = merged.get(CONF_ENTRY_TYPE, ENTRY_TYPE_WEATHER_HUB)

        if entry_type == ENTRY_TYPE_WEATHER_HUB:
            default_elev = (
                float(self.hass.config.elevation)
                if self.hass and self.hass.config.elevation is not None
                else DEFAULT_ELEVATION
            )
            schema = _build_weather_hub_schema(merged, default_elev)
        else:
            schema = _build_block_details_schema(merged)

        return self.async_show_form(step_id="init", data_schema=schema)
