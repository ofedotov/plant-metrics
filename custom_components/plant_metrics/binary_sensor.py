"""Binary sensor platform for Plant & Orchard Metrics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENTRY_TYPE, DOMAIN, ENTRY_TYPE_WEATHER_HUB
from .coordinator import PlantBlockCoordinator, WeatherHubCoordinator
from .entity import PlantMetricsBlockEntity, PlantMetricsWeatherHubEntity


@dataclass(frozen=True, kw_only=True)
class PlantMetricsHubBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Weather Hub binary sensor."""

    is_on_fn: Callable[[dict[str, Any]], bool | None]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


@dataclass(frozen=True, kw_only=True)
class PlantMetricsBlockBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Plant / Orchard Block binary sensor."""

    is_on_fn: Callable[[dict[str, Any]], bool | None]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


HUB_BINARY_SENSORS: tuple[PlantMetricsHubBinarySensorDescription, ...] = (
    PlantMetricsHubBinarySensorDescription(
        key="foliar_spray_window",
        name="Foliar Spray Window Suitable",
        icon="mdi:spray",
        is_on_fn=lambda d: bool(d.get("spray_window_suitable")),
        attr_fn=lambda d: {
            "score_pct": d.get("spray_window_score"),
            "reasons": d.get("spray_window_reasons"),
            "delta_t_c": d.get("delta_t_c"),
            "wind_kmh": d.get("wind_kmh"),
        },
    ),
    PlantMetricsHubBinarySensorDescription(
        key="wind_pollination_window",
        name="Wind Pollination Window Favorable",
        icon="mdi:weather-windy",
        is_on_fn=lambda d: bool(d.get("wind_pollination_favorable")),
        attr_fn=lambda d: {
            "score_pct": d.get("wind_pollination_score"),
            "advisory": d.get("wind_pollination_note"),
        },
    ),
    PlantMetricsHubBinarySensorDescription(
        key="bee_pollination_window",
        name="Bee & Insect Pollination Window Favorable",
        icon="mdi:bee-flower",
        is_on_fn=lambda d: bool(d.get("bee_pollination_favorable")),
        attr_fn=lambda d: {
            "score_pct": d.get("bee_pollination_score"),
            "advisory": d.get("bee_pollination_note"),
        },
    ),
    PlantMetricsHubBinarySensorDescription(
        key="virtual_leaf_wet",
        name="Foliage Wet",
        icon="mdi:water",
        device_class=BinarySensorDeviceClass.MOISTURE,
        is_on_fn=lambda d: bool(d.get("is_leaf_wet")),
        attr_fn=lambda d: {
            "wetness_pct": d.get("virtual_leaf_wetness_pct"),
            "continuous_lwd_hours": d.get("continuous_lwd_hours"),
        },
    ),
)


BLOCK_BINARY_SENSORS: tuple[PlantMetricsBlockBinarySensorDescription, ...] = (
    PlantMetricsBlockBinarySensorDescription(
        key="irrigation_needed",
        name="Irrigation Needed",
        icon="mdi:water-alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda d: bool(d.get("irrigation_needed")),
        attr_fn=lambda d: {
            "water_deficit_mm": d.get("water_deficit_mm"),
            "raw_threshold_mm": d.get("raw_threshold_mm"),
            "depletion_pct": d.get("root_zone_depletion_pct"),
            "recommended_liters_per_plant": d.get(
                "recommended_irrigation_liters_per_plant"
            ),
            "soil_moisture_avg_pct": d.get("soil_moisture_avg_pct"),
        },
    ),
    PlantMetricsBlockBinarySensorDescription(
        key="frost_alert",
        name="Stage-Aware Frost Alert",
        icon="mdi:snowflake-alert",
        device_class=BinarySensorDeviceClass.COLD,
        is_on_fn=lambda d: d.get("frost_risk_level") in ("warning", "critical_damage"),
        attr_fn=lambda d: {
            "risk_level": d.get("frost_risk_level"),
            **(d.get("frost_attrs") or {}),
        },
    ),
    PlantMetricsBlockBinarySensorDescription(
        key="leaf_scorch_vpd_alert",
        name="Leaf Scorch & High VPD Stress Alert",
        icon="mdi:weather-sunny-alert",
        device_class=BinarySensorDeviceClass.HEAT,
        is_on_fn=lambda d: d.get("vpd_stress_state")
        in ("high_stress", "leaf_scorch_risk"),
        attr_fn=lambda d: {
            "stress_state": d.get("vpd_stress_state"),
            "canopy_vpd_kpa": d.get("canopy_vpd_kpa"),
            "canopy_temp_c": d.get("canopy_temp_c"),
            "advisory": d.get("vpd_stress_note"),
        },
    ),
    PlantMetricsBlockBinarySensorDescription(
        key="early_pest_spray_window",
        name="Early-Season Pest Treatment Window",
        icon="mdi:bug-check",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda d: d.get("early_pest_status") == "peak_migration_spray_window",
        attr_fn=lambda d: {
            "target_pest": d.get("early_pest_name"),
            "status": d.get("early_pest_status"),
            "gdd_6c": d.get("gdd_6c"),
            "advisory": d.get("early_pest_note"),
        },
    ),
    PlantMetricsBlockBinarySensorDescription(
        key="mid_pest_activity_alert",
        name="Mid-Season Pest Active Oviposition Alert",
        icon="mdi:bug-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda d: d.get("mid_pest_status")
        == "active_adult_oviposition_window",
        attr_fn=lambda d: {
            "target_pest": d.get("mid_pest_name"),
            "status": d.get("mid_pest_status"),
            "gdd_7c": d.get("gdd_7c"),
            "soil_temp_c": d.get("soil_temp_c"),
            "advisory": d.get("mid_pest_note"),
        },
    ),
    PlantMetricsBlockBinarySensorDescription(
        key="high_disease_infection_risk",
        name="High Disease or Desiccation Risk Alert",
        icon="mdi:biohazard",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda d: max(
            float(d.get("primary_disease_pct", 0.0)),
            float(d.get("foliar_disease_pct", 0.0)),
            float(d.get("rot_disease_pct", 0.0)),
        )
        >= 45.0,
        attr_fn=lambda d: {
            "primary_disease": d.get("primary_disease_name"),
            "primary_disease_risk_pct": d.get("primary_disease_pct"),
            "foliar_disease": d.get("foliar_disease_name"),
            "foliar_disease_risk_pct": d.get("foliar_disease_pct"),
            "rot_or_desiccation": d.get("rot_disease_name"),
            "rot_or_desiccation_risk_pct": d.get("rot_disease_pct"),
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Plant & Orchard Metrics binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entry_type = entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_WEATHER_HUB)

    if entry_type == ENTRY_TYPE_WEATHER_HUB:
        async_add_entities(
            PlantMetricsHubBinarySensor(coordinator, desc)
            for desc in HUB_BINARY_SENSORS
        )
    else:
        async_add_entities(
            PlantMetricsBlockBinarySensor(coordinator, desc)
            for desc in BLOCK_BINARY_SENSORS
        )


class PlantMetricsHubBinarySensor(PlantMetricsWeatherHubEntity, BinarySensorEntity):
    """Binary sensor for Weather Hub."""

    entity_description: PlantMetricsHubBinarySensorDescription

    def __init__(
        self,
        coordinator: WeatherHubCoordinator,
        description: PlantMetricsHubBinarySensorDescription,
    ) -> None:
        """Initialize Weather Hub binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None
        return self.entity_description.is_on_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if not self.coordinator.data or not self.entity_description.attr_fn:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)


class PlantMetricsBlockBinarySensor(PlantMetricsBlockEntity, BinarySensorEntity):
    """Binary sensor for Plant / Orchard Block."""

    entity_description: PlantMetricsBlockBinarySensorDescription

    def __init__(
        self,
        coordinator: PlantBlockCoordinator,
        description: PlantMetricsBlockBinarySensorDescription,
    ) -> None:
        """Initialize Plant Block binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None
        return self.entity_description.is_on_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if not self.coordinator.data or not self.entity_description.attr_fn:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)
