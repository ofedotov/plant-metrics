"""DataUpdateCoordinators for Weather Hub and Multi-Species Plant / Orchard Blocks."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .calculations import (
    calc_air_vpd_kpa,
    calc_canopy_vpd_kpa,
    calc_delta_t_c,
    calc_dew_point_c,
    calc_dli_increment_mol,
    calc_fao56_hourly_et0_mm,
    calc_gdd_increment,
    calc_ppfd_umol,
    calc_utah_chill_rate,
    calc_virtual_leaf_wetness_pct,
    calc_wet_bulb_c,
    clamp,
    estimate_canopy_temperature_c,
    evaluate_chill_and_bloom_sync,
    evaluate_early_pest_status,
    evaluate_foliar_disease_risk,
    evaluate_insect_pollination_window,
    evaluate_late_pest_status,
    evaluate_mid_pest_status,
    evaluate_plant_pollination_window,
    evaluate_plant_vpd_stress,
    evaluate_primary_disease_risk,
    evaluate_rot_or_desiccation_risk,
    evaluate_spray_window,
    evaluate_stage_frost_risk,
    evaluate_wind_pollination_window,
    infer_plant_phenology_stage,
    is_chill_hour,
    to_celsius,
    to_mm,
    to_pressure_kpa,
    to_solar_wm2,
    to_wind_ms,
)
from .const import (
    CONF_AVAILABLE_WATER_CAPACITY_MM_M,
    CONF_BIOFIX_START_MONTH,
    CONF_BLOCK_NAME,
    CONF_CANOPY_AREA_M2,
    CONF_CANOPY_TEMP_ENTITY,
    CONF_DORMANCY_START_MONTH,
    CONF_ELEVATION,
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
    CONF_WIND_GUST_ENTITY,
    CONF_WIND_SPEED_ENTITY,
    DEFAULT_AWC_MM_M,
    DEFAULT_BIOFIX_START_MONTH,
    DEFAULT_DORMANCY_START_MONTH,
    DEFAULT_ELEVATION,
    DEFAULT_IRRIGATION_EFFICIENCY,
    DEFAULT_PLANTS_COUNT,
    DOMAIN,
    KC_BY_SPECIES_AND_STAGE,
    PHENOLOGY_STAGES,
    SPECIES_GENERIC,
    STAGE_DORMANT,
)
from .plants import PlantProfile, get_plant_profile

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
SAVE_DELAY_SECONDS = 180
UPDATE_INTERVAL_SECONDS = 60


def _read_float_state(
    hass: HomeAssistant, entity_id: str | None
) -> tuple[float | None, str | None]:
    """Read a numeric state and its unit_of_measurement from Home Assistant."""
    if not entity_id:
        return None, None
    state = hass.states.get(entity_id)
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
        return None, None
    try:
        val = float(state.state)
    except (ValueError, TypeError):
        return None, None
    unit = state.attributes.get("unit_of_measurement")
    return val, unit


class WeatherHubCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator calculating site-wide microclimate metrics from weather station sensors."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the Weather Hub coordinator."""
        self.entry = entry
        self.site_name: str = entry.data.get(CONF_SITE_NAME, entry.title)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_weather_hub_{entry.entry_id}",
        )
        self._store = Store[dict[str, Any]](
            hass, STORAGE_VERSION, f"{DOMAIN}.weather_hub.{entry.entry_id}"
        )
        self._unsub_state_listener: Any = None
        self._unsub_timer: Any = None
        self._block_listeners: list[Any] = []

        # Persistent daily & continuous accumulators
        self._last_update_ts: float | None = None
        self._current_day_str: str = dt_util.now().strftime("%Y-%m-%d")
        self.et0_daily_mm: float = 0.0
        self.et0_yesterday_mm: float = 0.0
        self.dli_daily_mol: float = 0.0
        self.dli_yesterday_mol: float = 0.0
        self.peak_vpd_daily_kpa: float = 0.0
        self.virtual_leaf_wetness_pct: float = 0.0
        self.continuous_lwd_hours: float = 0.0
        self.dry_grace_hours: float = 0.0
        self.mildew_favorable_hours: float = 0.0
        self.last_rain_daily_mm: float | None = None
        self.last_rain_delta_mm: float = 0.0

    def get_cfg(self, key: str, default: Any = None) -> Any:
        """Retrieve config value from options with fallback to data."""
        if key in self.entry.options:
            return self.entry.options[key]
        return self.entry.data.get(key, default)

    def register_block_callback(self, cb: Any) -> Any:
        """Register a PlantBlockCoordinator callback to run whenever site weather updates."""
        self._block_listeners.append(cb)

        def _remove() -> None:
            if cb in self._block_listeners:
                self._block_listeners.remove(cb)

        return _remove

    async def async_setup(self) -> None:
        """Load stored accumulator state and start listeners."""
        stored = await self._store.async_load()
        if stored:
            self._current_day_str = stored.get("current_day_str", self._current_day_str)
            self.et0_daily_mm = float(stored.get("et0_daily_mm", 0.0))
            self.et0_yesterday_mm = float(stored.get("et0_yesterday_mm", 0.0))
            self.dli_daily_mol = float(stored.get("dli_daily_mol", 0.0))
            self.dli_yesterday_mol = float(stored.get("dli_yesterday_mol", 0.0))
            self.peak_vpd_daily_kpa = float(stored.get("peak_vpd_daily_kpa", 0.0))
            self.virtual_leaf_wetness_pct = float(
                stored.get("virtual_leaf_wetness_pct", 0.0)
            )
            self.continuous_lwd_hours = float(stored.get("continuous_lwd_hours", 0.0))
            self.dry_grace_hours = float(stored.get("dry_grace_hours", 0.0))
            self.mildew_favorable_hours = float(
                stored.get("mildew_favorable_hours", 0.0)
            )
            self.last_rain_daily_mm = stored.get("last_rain_daily_mm")
            self._last_update_ts = stored.get("last_update_ts")

        watched_entities = [
            e
            for e in (
                self.get_cfg(CONF_TEMP_ENTITY),
                self.get_cfg(CONF_HUMIDITY_ENTITY),
                self.get_cfg(CONF_WIND_SPEED_ENTITY),
                self.get_cfg(CONF_WIND_GUST_ENTITY),
                self.get_cfg(CONF_SOLAR_RAD_ENTITY),
                self.get_cfg(CONF_PRESSURE_ENTITY),
                self.get_cfg(CONF_RAIN_RATE_ENTITY),
                self.get_cfg(CONF_RAIN_DAILY_ENTITY),
                self.get_cfg(CONF_UV_ENTITY),
            )
            if e
        ]

        if watched_entities:
            self._unsub_state_listener = async_track_state_change_event(
                self.hass, watched_entities, self._handle_source_change
            )

        self._unsub_timer = async_track_time_interval(
            self.hass,
            self._handle_timer,
            timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )

        await self.async_refresh()

    async def async_shutdown(self) -> None:
        """Clean up listeners and save state."""
        if self._unsub_state_listener:
            self._unsub_state_listener()
            self._unsub_state_listener = None
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        await self._async_save_state()

    @callback
    def _handle_source_change(self, event: Event) -> None:
        """Handle state changes from weather station entities."""
        self.hass.async_create_task(self.async_request_refresh())

    async def _handle_timer(self, _now: datetime) -> None:
        """Periodic integration tick."""
        await self.async_request_refresh()

    def _serialize_hub_state(self) -> dict[str, Any]:
        """Serialize persistent hub state."""
        return {
            "current_day_str": self._current_day_str,
            "et0_daily_mm": round(self.et0_daily_mm, 4),
            "et0_yesterday_mm": round(self.et0_yesterday_mm, 3),
            "dli_daily_mol": round(self.dli_daily_mol, 4),
            "dli_yesterday_mol": round(self.dli_yesterday_mol, 2),
            "peak_vpd_daily_kpa": round(self.peak_vpd_daily_kpa, 3),
            "virtual_leaf_wetness_pct": round(self.virtual_leaf_wetness_pct, 2),
            "continuous_lwd_hours": round(self.continuous_lwd_hours, 3),
            "dry_grace_hours": round(self.dry_grace_hours, 3),
            "mildew_favorable_hours": round(self.mildew_favorable_hours, 3),
            "last_rain_daily_mm": self.last_rain_daily_mm,
            "last_update_ts": self._last_update_ts,
        }

    async def _async_save_state(self) -> None:
        """Persist current accumulators."""
        await self._store.async_save(self._serialize_hub_state())

    def _schedule_save(self) -> None:
        """Schedule delayed write to storage."""
        self._store.async_delay_save(self._serialize_hub_state, SAVE_DELAY_SECONDS)

    async def _async_update_data(self) -> dict[str, Any]:
        """Compute site-wide microclimate metrics and integrate time-based totals."""
        now = dt_util.now()
        now_ts = now.timestamp()
        today_str = now.strftime("%Y-%m-%d")

        if today_str != self._current_day_str:
            self.et0_yesterday_mm = round(self.et0_daily_mm, 3)
            self.dli_yesterday_mol = round(self.dli_daily_mol, 2)
            self.et0_daily_mm = 0.0
            self.dli_daily_mol = 0.0
            self.peak_vpd_daily_kpa = 0.0
            self.last_rain_daily_mm = 0.0
            self._current_day_str = today_str

        dt_seconds = 0.0
        if self._last_update_ts is not None:
            dt_seconds = clamp(now_ts - self._last_update_ts, 0.0, 900.0)
        self._last_update_ts = now_ts
        dt_hours = dt_seconds / 3600.0

        raw_temp, temp_unit = _read_float_state(
            self.hass, self.get_cfg(CONF_TEMP_ENTITY)
        )
        raw_rh, _ = _read_float_state(self.hass, self.get_cfg(CONF_HUMIDITY_ENTITY))
        raw_wind, wind_unit = _read_float_state(
            self.hass, self.get_cfg(CONF_WIND_SPEED_ENTITY)
        )
        raw_gust, gust_unit = _read_float_state(
            self.hass, self.get_cfg(CONF_WIND_GUST_ENTITY)
        )
        raw_solar, solar_unit = _read_float_state(
            self.hass, self.get_cfg(CONF_SOLAR_RAD_ENTITY)
        )
        raw_pressure, pressure_unit = _read_float_state(
            self.hass, self.get_cfg(CONF_PRESSURE_ENTITY)
        )
        raw_rain_rate, rain_rate_unit = _read_float_state(
            self.hass, self.get_cfg(CONF_RAIN_RATE_ENTITY)
        )
        raw_rain_daily, rain_daily_unit = _read_float_state(
            self.hass, self.get_cfg(CONF_RAIN_DAILY_ENTITY)
        )
        raw_uv, _ = _read_float_state(self.hass, self.get_cfg(CONF_UV_ENTITY))

        temp_c = to_celsius(raw_temp, temp_unit) if raw_temp is not None else None
        rh_pct = clamp(raw_rh, 1.0, 100.0) if raw_rh is not None else None
        wind_ms = to_wind_ms(raw_wind, wind_unit) if raw_wind is not None else 0.0
        wind_kmh = round(wind_ms * 3.6, 2)
        gust_ms = to_wind_ms(raw_gust, gust_unit) if raw_gust is not None else None
        gust_kmh = round(gust_ms * 3.6, 2) if gust_ms is not None else None
        solar_wm2 = (
            to_solar_wm2(raw_solar, solar_unit) if raw_solar is not None else 0.0
        )
        pressure_kpa = (
            to_pressure_kpa(raw_pressure, pressure_unit)
            if raw_pressure is not None
            else None
        )
        rain_rate_mmh = (
            to_mm(raw_rain_rate, rain_rate_unit) if raw_rain_rate is not None else 0.0
        )
        rain_daily_mm = (
            to_mm(raw_rain_daily, rain_daily_unit)
            if raw_rain_daily is not None
            else 0.0
        )
        elevation_m = float(self.get_cfg(CONF_ELEVATION, DEFAULT_ELEVATION))

        rain_delta_mm = 0.0
        if raw_rain_daily is not None:
            if (
                self.last_rain_daily_mm is not None
                and rain_daily_mm >= self.last_rain_daily_mm
            ):
                rain_delta_mm = rain_daily_mm - self.last_rain_daily_mm
            elif (
                self.last_rain_daily_mm is not None
                and rain_daily_mm < self.last_rain_daily_mm
            ):
                rain_delta_mm = rain_daily_mm
            self.last_rain_daily_mm = rain_daily_mm
        elif rain_rate_mmh > 0.0 and dt_hours > 0.0:
            rain_delta_mm = rain_rate_mmh * dt_hours
        self.last_rain_delta_mm = rain_delta_mm

        if temp_c is not None and rh_pct is not None:
            dew_point_c = calc_dew_point_c(temp_c, rh_pct)
            dew_depression_c = round(max(0.0, temp_c - dew_point_c), 2)
            wet_bulb_c = calc_wet_bulb_c(temp_c, rh_pct)
            delta_t_c = calc_delta_t_c(temp_c, wet_bulb_c)
            air_vpd_kpa = calc_air_vpd_kpa(temp_c, rh_pct)
            if air_vpd_kpa > self.peak_vpd_daily_kpa:
                self.peak_vpd_daily_kpa = air_vpd_kpa

            et0_hourly_mm = calc_fao56_hourly_et0_mm(
                temp_c=temp_c,
                rh_pct=rh_pct,
                wind_speed_ms=wind_ms,
                solar_rad_wm2=solar_wm2,
                pressure_kpa=pressure_kpa,
                elevation_m=elevation_m,
            )
            et0_increment_mm = et0_hourly_mm * dt_hours
            self.et0_daily_mm += et0_increment_mm

            self.virtual_leaf_wetness_pct = calc_virtual_leaf_wetness_pct(
                temp_c=temp_c,
                dew_point_c=dew_point_c,
                rh_pct=rh_pct,
                rain_rate_mmh=rain_rate_mmh,
                solar_rad_wm2=solar_wm2,
                wind_speed_ms=wind_ms,
                prev_wetness_pct=self.virtual_leaf_wetness_pct,
                dt_seconds=max(1.0, dt_seconds),
            )
            is_leaf_wet = self.virtual_leaf_wetness_pct >= 50.0
            if is_leaf_wet:
                self.continuous_lwd_hours += dt_hours
                self.dry_grace_hours = 0.0
            else:
                self.dry_grace_hours += dt_hours
                if self.dry_grace_hours >= 2.0:
                    self.continuous_lwd_hours = max(
                        0.0, self.continuous_lwd_hours - dt_hours * 3.0
                    )

            if 16.0 <= temp_c <= 28.0 and rh_pct >= 65.0 and rain_rate_mmh < 2.0:
                self.mildew_favorable_hours = clamp(
                    self.mildew_favorable_hours + dt_hours, 0.0, 48.0
                )
            else:
                decay = dt_hours * (2.0 if rain_rate_mmh >= 2.0 else 0.35)
                self.mildew_favorable_hours = max(
                    0.0, self.mildew_favorable_hours - decay
                )

            spray_ok, spray_score, spray_reasons = evaluate_spray_window(
                delta_t_c=delta_t_c,
                wind_speed_kmh=wind_kmh,
                wind_gust_kmh=gust_kmh,
                rain_rate_mmh=rain_rate_mmh,
                temp_c=temp_c,
            )
            wind_pollen_ok, wind_pollen_score, wind_pollen_note = (
                evaluate_wind_pollination_window(
                    temp_c=temp_c,
                    rh_pct=rh_pct,
                    wind_speed_kmh=wind_kmh,
                    rain_rate_mmh=rain_rate_mmh,
                )
            )
            bee_pollen_ok, bee_pollen_score, bee_pollen_note = (
                evaluate_insect_pollination_window(
                    temp_c=temp_c,
                    rh_pct=rh_pct,
                    wind_speed_kmh=wind_kmh,
                    rain_rate_mmh=rain_rate_mmh,
                    solar_rad_wm2=solar_wm2,
                )
            )
        else:
            dew_point_c = None
            dew_depression_c = None
            wet_bulb_c = None
            delta_t_c = None
            air_vpd_kpa = None
            et0_hourly_mm = 0.0
            et0_increment_mm = 0.0
            is_leaf_wet = False
            spray_ok = False
            spray_score = 0.0
            spray_reasons = ["Waiting for temperature and humidity sensor data."]
            wind_pollen_ok = False
            wind_pollen_score = 0.0
            wind_pollen_note = "Waiting for temperature and humidity sensor data."
            bee_pollen_ok = False
            bee_pollen_score = 0.0
            bee_pollen_note = "Waiting for temperature and humidity sensor data."

        ppfd_umol = calc_ppfd_umol(solar_wm2)
        self.dli_daily_mol += calc_dli_increment_mol(ppfd_umol, dt_seconds)

        self._schedule_save()

        data = {
            "timestamp": now_ts,
            "dt_seconds": dt_seconds,
            "temp_c": round(temp_c, 2) if temp_c is not None else None,
            "rh_pct": round(rh_pct, 1) if rh_pct is not None else None,
            "wind_ms": round(wind_ms, 2),
            "wind_kmh": wind_kmh,
            "gust_kmh": gust_kmh,
            "solar_wm2": round(solar_wm2, 1),
            "pressure_kpa": (
                round(pressure_kpa, 2) if pressure_kpa is not None else None
            ),
            "rain_rate_mmh": round(rain_rate_mmh, 2),
            "rain_daily_mm": round(rain_daily_mm, 2),
            "rain_delta_mm": round(rain_delta_mm, 4),
            "uv_index": raw_uv,
            "dew_point_c": dew_point_c,
            "dew_depression_c": dew_depression_c,
            "wet_bulb_c": wet_bulb_c,
            "delta_t_c": delta_t_c,
            "air_vpd_kpa": air_vpd_kpa,
            "peak_vpd_daily_kpa": round(self.peak_vpd_daily_kpa, 3),
            "ppfd_umol": ppfd_umol,
            "dli_daily_mol": round(self.dli_daily_mol, 2),
            "dli_yesterday_mol": round(self.dli_yesterday_mol, 2),
            "et0_hourly_mm": round(et0_hourly_mm, 3),
            "et0_increment_mm": et0_increment_mm,
            "et0_daily_mm": round(self.et0_daily_mm, 2),
            "et0_yesterday_mm": round(self.et0_yesterday_mm, 2),
            "virtual_leaf_wetness_pct": round(self.virtual_leaf_wetness_pct, 1),
            "is_leaf_wet": is_leaf_wet,
            "continuous_lwd_hours": round(self.continuous_lwd_hours, 2),
            "mildew_favorable_hours": round(self.mildew_favorable_hours, 2),
            "spray_window_suitable": spray_ok,
            "spray_window_score": spray_score,
            "spray_window_reasons": spray_reasons,
            "wind_pollination_favorable": wind_pollen_ok,
            "wind_pollination_score": wind_pollen_score,
            "wind_pollination_note": wind_pollen_note,
            "bee_pollination_favorable": bee_pollen_ok,
            "bee_pollination_score": bee_pollen_score,
            "bee_pollination_note": bee_pollen_note,
        }

        for cb in list(self._block_listeners):
            cb(data)

        return data


class PlantBlockCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator calculating species- & cultivar-specific metrics for a plant block."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        weather_hub: WeatherHubCoordinator,
    ) -> None:
        """Initialize the Plant Block coordinator."""
        self.entry = entry
        self.weather_hub = weather_hub
        self.block_name: str = entry.data.get(CONF_BLOCK_NAME, entry.title)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_block_{entry.entry_id}",
        )
        self._store = Store[dict[str, Any]](
            hass, STORAGE_VERSION, f"{DOMAIN}.plant_block.{entry.entry_id}"
        )
        self._unsub_hub: Any = None
        self._unsub_state_listener: Any = None

        now = dt_util.now()
        self._current_day_str: str = now.strftime("%Y-%m-%d")
        self._dormancy_season_year: int = self._compute_season_year(
            now,
            int(
                self.get_cfg(
                    CONF_DORMANCY_START_MONTH, DEFAULT_DORMANCY_START_MONTH
                )
            ),
        )
        self._biofix_season_year: int = self._compute_season_year(
            now,
            int(self.get_cfg(CONF_BIOFIX_START_MONTH, DEFAULT_BIOFIX_START_MONTH)),
        )

        self.chill_hours: float = 0.0
        self.utah_chill_units: float = 0.0
        self.gdd_custom: float = 0.0
        self.gdd_6c: float = 0.0
        self.gdd_7c: float = 0.0
        self.gdd_10c: float = 0.0
        self.etc_daily_mm: float = 0.0
        self.etc_yesterday_mm: float = 0.0
        self.water_deficit_mm: float = 0.0
        self.phenology_stage: str = STAGE_DORMANT
        self.auto_stage_enabled: bool = True
        self.last_irrigation_ts: str | None = None
        self.last_irrigation_mm: float = 0.0

    @staticmethod
    def _compute_season_year(now: datetime, start_month: int) -> int:
        """Return the starting calendar year of the current phenological cycle."""
        return now.year if now.month >= start_month else (now.year - 1)

    def get_cfg(self, key: str, default: Any = None) -> Any:
        """Retrieve config value from options with fallback to data."""
        if key in self.entry.options:
            return self.entry.options[key]
        return self.entry.data.get(key, default)

    @property
    def profile_key(self) -> str:
        """Return configured plant profile key."""
        return str(self.get_cfg(CONF_PLANT_PROFILE, "hazelnut_tonda_gentile"))

    @property
    def plant_profile(self) -> PlantProfile:
        """Return the PlantProfile for this block."""
        return get_plant_profile(self.profile_key)

    async def async_setup(self) -> None:
        """Load stored block state and subscribe to weather hub & soil sensors."""
        stored = await self._store.async_load()
        if stored:
            self._current_day_str = stored.get("current_day_str", self._current_day_str)
            self._dormancy_season_year = int(
                stored.get("dormancy_season_year", self._dormancy_season_year)
            )
            self._biofix_season_year = int(
                stored.get("biofix_season_year", self._biofix_season_year)
            )
            self.chill_hours = float(stored.get("chill_hours", 0.0))
            self.utah_chill_units = float(stored.get("utah_chill_units", 0.0))
            self.gdd_custom = float(stored.get("gdd_custom", 0.0))
            self.gdd_6c = float(stored.get("gdd_6c", 0.0))
            self.gdd_7c = float(stored.get("gdd_7c", 0.0))
            self.gdd_10c = float(stored.get("gdd_10c", 0.0))
            self.etc_daily_mm = float(stored.get("etc_daily_mm", 0.0))
            self.etc_yesterday_mm = float(stored.get("etc_yesterday_mm", 0.0))
            self.water_deficit_mm = float(stored.get("water_deficit_mm", 0.0))
            stage = stored.get("phenology_stage", STAGE_DORMANT)
            self.phenology_stage = (
                stage if stage in PHENOLOGY_STAGES else STAGE_DORMANT
            )
            self.auto_stage_enabled = bool(stored.get("auto_stage_enabled", True))
            self.last_irrigation_ts = stored.get("last_irrigation_ts")
            self.last_irrigation_mm = float(stored.get("last_irrigation_mm", 0.0))

        self._unsub_hub = self.weather_hub.register_block_callback(
            self._handle_hub_update
        )

        soil_moisture_list = self.get_cfg(CONF_SOIL_MOISTURE_ENTITIES) or []
        if isinstance(soil_moisture_list, str):
            soil_moisture_list = [soil_moisture_list]
        block_entities = [
            e
            for e in (
                *soil_moisture_list,
                self.get_cfg(CONF_SOIL_TEMP_ENTITY),
                self.get_cfg(CONF_CANOPY_TEMP_ENTITY),
            )
            if e
        ]
        if block_entities:
            self._unsub_state_listener = async_track_state_change_event(
                self.hass, block_entities, self._handle_block_sensor_change
            )

        await self.async_refresh()

    async def async_shutdown(self) -> None:
        """Unsubscribe listeners and persist state."""
        if self._unsub_hub:
            self._unsub_hub()
            self._unsub_hub = None
        if self._unsub_state_listener:
            self._unsub_state_listener()
            self._unsub_state_listener = None
        await self._async_save_state()

    @callback
    def _handle_hub_update(self, _hub_data: dict[str, Any]) -> None:
        """Trigger block calculation update when Weather Hub updates."""
        self.hass.async_create_task(self.async_request_refresh())

    @callback
    def _handle_block_sensor_change(self, _event: Event) -> None:
        """Trigger refresh when WH51/WN31 block sensors change."""
        self.hass.async_create_task(self.async_request_refresh())

    def _state_dict(self) -> dict[str, Any]:
        """Serialize persistent state."""
        return {
            "current_day_str": self._current_day_str,
            "dormancy_season_year": self._dormancy_season_year,
            "biofix_season_year": self._biofix_season_year,
            "chill_hours": round(self.chill_hours, 3),
            "utah_chill_units": round(self.utah_chill_units, 3),
            "gdd_custom": round(self.gdd_custom, 3),
            "gdd_6c": round(self.gdd_6c, 3),
            "gdd_7c": round(self.gdd_7c, 3),
            "gdd_10c": round(self.gdd_10c, 3),
            "etc_daily_mm": round(self.etc_daily_mm, 4),
            "etc_yesterday_mm": round(self.etc_yesterday_mm, 3),
            "water_deficit_mm": round(self.water_deficit_mm, 3),
            "phenology_stage": self.phenology_stage,
            "auto_stage_enabled": self.auto_stage_enabled,
            "last_irrigation_ts": self.last_irrigation_ts,
            "last_irrigation_mm": round(self.last_irrigation_mm, 2),
        }

    async def _async_save_state(self) -> None:
        """Save persistent state immediately."""
        await self._store.async_save(self._state_dict())

    def _schedule_save(self) -> None:
        """Schedule delayed save."""
        self._store.async_delay_save(self._state_dict, SAVE_DELAY_SECONDS)

    # -------------------------------------------------------------------------
    # User Actions / Services / Entity Controls
    # -------------------------------------------------------------------------

    async def async_set_phenology_stage(self, stage: str) -> None:
        """Manually set the active plant phenology stage."""
        if stage in PHENOLOGY_STAGES:
            self.phenology_stage = stage
            await self._async_save_state()
            await self.async_request_refresh()

    async def async_set_auto_stage(self, enabled: bool) -> None:
        """Enable or disable automatic GDD/Chill phenology stage progression."""
        self.auto_stage_enabled = enabled
        await self._async_save_state()
        await self.async_request_refresh()

    async def async_log_irrigation(
        self, amount_mm: float | None = None, liters_per_tree: float | None = None
    ) -> None:
        """Record an irrigation event in mm or liters/plant and reduce water deficit."""
        profile = self.plant_profile
        canopy_m2 = max(
            0.5,
            float(
                self.get_cfg(CONF_CANOPY_AREA_M2, profile.default_canopy_area_m2)
            ),
        )
        eff = clamp(
            float(
                self.get_cfg(
                    CONF_IRRIGATION_EFFICIENCY, DEFAULT_IRRIGATION_EFFICIENCY
                )
            ),
            0.3,
            1.0,
        )
        added_mm = 0.0
        if amount_mm is not None and amount_mm > 0:
            added_mm = amount_mm * eff
        elif liters_per_tree is not None and liters_per_tree > 0:
            added_mm = (liters_per_tree / canopy_m2) * eff

        if added_mm > 0:
            self.water_deficit_mm = max(0.0, self.water_deficit_mm - added_mm)
            self.last_irrigation_mm = round(added_mm, 2)
            self.last_irrigation_ts = dt_util.now().isoformat()
            await self._async_save_state()
            await self.async_request_refresh()

    async def async_reset_water_balance(self) -> None:
        """Reset cumulative water deficit to 0.0 mm (field capacity)."""
        self.water_deficit_mm = 0.0
        self.last_irrigation_ts = dt_util.now().isoformat()
        await self._async_save_state()
        await self.async_request_refresh()

    async def async_reset_seasonal_accumulators(self) -> None:
        """Reset seasonal Chill Hours, Utah Chill Units, and GDD counters."""
        self.chill_hours = 0.0
        self.utah_chill_units = 0.0
        self.gdd_custom = 0.0
        self.gdd_6c = 0.0
        self.gdd_7c = 0.0
        self.gdd_10c = 0.0
        await self._async_save_state()
        await self.async_request_refresh()

    async def async_set_chill_units(self, value: float) -> None:
        """Allow manual adjustment/seeding of Utah Chill Units."""
        self.utah_chill_units = max(0.0, value)
        await self._async_save_state()
        await self.async_request_refresh()

    async def async_set_gdd(self, value: float) -> None:
        """Allow manual adjustment/seeding of seasonal GDD."""
        self.gdd_custom = max(0.0, value)
        await self._async_save_state()
        await self.async_request_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Compute species & cultivar block metrics from Weather Hub + block sensors."""
        now = dt_util.now()
        today_str = now.strftime("%Y-%m-%d")
        hub_data = self.weather_hub.data or {}

        if today_str != self._current_day_str:
            self.etc_yesterday_mm = round(self.etc_daily_mm, 3)
            self.etc_daily_mm = 0.0
            self._current_day_str = today_str

        dormancy_start_month = int(
            self.get_cfg(
                CONF_DORMANCY_START_MONTH, DEFAULT_DORMANCY_START_MONTH
            )
        )
        biofix_start_month = int(
            self.get_cfg(CONF_BIOFIX_START_MONTH, DEFAULT_BIOFIX_START_MONTH)
        )
        cur_dormancy_year = self._compute_season_year(now, dormancy_start_month)
        if cur_dormancy_year != self._dormancy_season_year:
            self.chill_hours = 0.0
            self.utah_chill_units = 0.0
            self._dormancy_season_year = cur_dormancy_year
            if self.auto_stage_enabled:
                self.phenology_stage = STAGE_DORMANT

        cur_biofix_year = self._compute_season_year(now, biofix_start_month)
        if cur_biofix_year != self._biofix_season_year:
            self.gdd_custom = 0.0
            self.gdd_6c = 0.0
            self.gdd_7c = 0.0
            self.gdd_10c = 0.0
            self._biofix_season_year = cur_biofix_year

        dt_seconds = float(hub_data.get("dt_seconds", 0.0))
        dt_hours = dt_seconds / 3600.0
        temp_c: float | None = hub_data.get("temp_c")
        rh_pct: float | None = hub_data.get("rh_pct")
        wind_ms: float = float(hub_data.get("wind_ms", 0.0))
        wind_kmh: float = float(hub_data.get("wind_kmh", 0.0))
        solar_wm2: float = float(hub_data.get("solar_wm2", 0.0))
        rain_rate_mmh: float = float(hub_data.get("rain_rate_mmh", 0.0))
        rain_daily_mm: float = float(hub_data.get("rain_daily_mm", 0.0))
        rain_delta_mm: float = float(hub_data.get("rain_delta_mm", 0.0))
        wet_bulb_c: float | None = hub_data.get("wet_bulb_c")
        et0_increment_mm: float = float(hub_data.get("et0_increment_mm", 0.0))
        et0_daily_mm: float = float(hub_data.get("et0_daily_mm", 0.0))
        lwd_hours: float = float(hub_data.get("continuous_lwd_hours", 0.0))
        mildew_favorable_hours: float = float(
            hub_data.get("mildew_favorable_hours", 0.0)
        )

        profile = self.plant_profile
        species = profile.species
        primary_chill_target = float(
            self.get_cfg(
                CONF_PRIMARY_CHILL_TARGET, profile.primary_chill_units
            )
        )
        secondary_chill_target = float(
            self.get_cfg(
                CONF_SECONDARY_CHILL_TARGET, profile.secondary_chill_units
            )
        )
        gdd_base_c = float(self.get_cfg(CONF_GDD_BASE_TEMP, profile.gdd_base_c))
        gdd_upper_c = float(
            self.get_cfg(CONF_GDD_UPPER_TEMP, profile.gdd_upper_c)
        )
        canopy_area_m2 = float(
            self.get_cfg(CONF_CANOPY_AREA_M2, profile.default_canopy_area_m2)
        )
        plants_count = int(
            self.get_cfg(CONF_PLANTS_COUNT, DEFAULT_PLANTS_COUNT)
        )
        root_depth_mm = float(
            self.get_cfg(CONF_ROOT_DEPTH_MM, profile.default_root_depth_mm)
        )
        awc_mm_m = float(
            self.get_cfg(CONF_AVAILABLE_WATER_CAPACITY_MM_M, DEFAULT_AWC_MM_M)
        )
        irrigation_eff = clamp(
            float(
                self.get_cfg(
                    CONF_IRRIGATION_EFFICIENCY, DEFAULT_IRRIGATION_EFFICIENCY
                )
            ),
            0.3,
            1.0,
        )

        soil_moisture_entities = self.get_cfg(CONF_SOIL_MOISTURE_ENTITIES) or []
        if isinstance(soil_moisture_entities, str):
            soil_moisture_entities = [soil_moisture_entities]
        soil_moisture_values: list[float] = []
        for entity_id in soil_moisture_entities:
            val, _ = _read_float_state(self.hass, entity_id)
            if val is not None:
                soil_moisture_values.append(clamp(val, 0.0, 100.0))
        soil_moisture_avg_pct = (
            round(sum(soil_moisture_values) / len(soil_moisture_values), 1)
            if soil_moisture_values
            else None
        )

        raw_soil_temp, soil_temp_unit = _read_float_state(
            self.hass, self.get_cfg(CONF_SOIL_TEMP_ENTITY)
        )
        soil_temp_c = (
            round(to_celsius(raw_soil_temp, soil_temp_unit), 2)
            if raw_soil_temp is not None
            else None
        )

        raw_canopy_temp, canopy_temp_unit = _read_float_state(
            self.hass, self.get_cfg(CONF_CANOPY_TEMP_ENTITY)
        )
        measured_canopy_temp_c = (
            round(to_celsius(raw_canopy_temp, canopy_temp_unit), 2)
            if raw_canopy_temp is not None
            else None
        )

        if temp_c is not None and dt_seconds > 0:
            if now.month in (10, 11, 12, 1, 2, 3, 4):
                if is_chill_hour(temp_c):
                    self.chill_hours += dt_hours
                utah_rate = calc_utah_chill_rate(temp_c)
                self.utah_chill_units = max(
                    0.0, self.utah_chill_units + utah_rate * dt_hours
                )

            if now.month >= biofix_start_month and now.month <= 10:
                self.gdd_custom += calc_gdd_increment(
                    temp_c, gdd_base_c, gdd_upper_c, dt_seconds
                )
                self.gdd_6c += calc_gdd_increment(
                    temp_c, 6.0, 30.0, dt_seconds
                )
                self.gdd_7c += calc_gdd_increment(
                    temp_c, 7.0, 31.0, dt_seconds
                )
                self.gdd_10c += calc_gdd_increment(
                    temp_c, 10.0, 31.0, dt_seconds
                )

        if self.auto_stage_enabled:
            self.phenology_stage = infer_plant_phenology_stage(
                utah_chill_units=self.utah_chill_units,
                primary_chill_target=primary_chill_target,
                secondary_chill_target=secondary_chill_target,
                gdd=self.gdd_custom,
                month=now.month,
                species=species,
            )

        species_kc_map = KC_BY_SPECIES_AND_STAGE.get(
            species, KC_BY_SPECIES_AND_STAGE[SPECIES_GENERIC]
        )
        kc = species_kc_map.get(self.phenology_stage, 0.50)
        etc_increment_mm = et0_increment_mm * kc
        self.etc_daily_mm = round(et0_daily_mm * kc, 3)

        taw_mm = round((root_depth_mm / 1000.0) * awc_mm_m, 1)
        raw_threshold_mm = round(taw_mm * profile.mad_fraction, 1)

        effective_rain_delta_mm = rain_delta_mm * 0.80
        self.water_deficit_mm = clamp(
            self.water_deficit_mm + etc_increment_mm - effective_rain_delta_mm,
            0.0,
            taw_mm,
        )

        daily_plant_liters = round(
            (self.etc_daily_mm * canopy_area_m2) / irrigation_eff, 2
        )
        daily_block_liters = round(daily_plant_liters * plants_count, 1)

        depletion_pct = round(
            clamp((self.water_deficit_mm / max(1.0, taw_mm)) * 100.0, 0.0, 100.0), 1
        )
        irrigation_needed_by_deficit = self.water_deficit_mm >= raw_threshold_mm
        if soil_moisture_avg_pct is not None:
            irrigation_needed = (
                irrigation_needed_by_deficit or soil_moisture_avg_pct < 35.0
            ) and soil_moisture_avg_pct < 65.0
        else:
            irrigation_needed = irrigation_needed_by_deficit

        recommended_irrigation_liters_per_plant = (
            round((self.water_deficit_mm * canopy_area_m2) / irrigation_eff, 1)
            if self.water_deficit_mm > 1.0
            else 0.0
        )

        if measured_canopy_temp_c is not None:
            canopy_temp_c = measured_canopy_temp_c
        elif temp_c is not None and rh_pct is not None:
            canopy_temp_c = estimate_canopy_temperature_c(
                air_temp_c=temp_c,
                rh_pct=rh_pct,
                solar_rad_wm2=solar_wm2,
                wind_speed_ms=wind_ms,
                vpd_closure_kpa=profile.vpd_optimal_max_kpa,
            )
        else:
            canopy_temp_c = None

        if canopy_temp_c is not None and temp_c is not None and rh_pct is not None:
            canopy_vpd_kpa = calc_canopy_vpd_kpa(temp_c, rh_pct, canopy_temp_c)
            vpd_stress_state, vpd_stress_note = evaluate_plant_vpd_stress(
                canopy_vpd_kpa=canopy_vpd_kpa,
                canopy_temp_c=canopy_temp_c,
                wind_speed_kmh=wind_kmh,
                optimal_max_kpa=profile.vpd_optimal_max_kpa,
                high_stress_kpa=profile.vpd_high_stress_kpa,
                scorch_kpa=profile.vpd_scorch_kpa,
            )
            block_pollen_ok, block_pollen_score, block_pollen_note = (
                evaluate_plant_pollination_window(
                    pollination_type=profile.pollination_type,
                    temp_c=temp_c,
                    rh_pct=rh_pct,
                    wind_speed_kmh=wind_kmh,
                    rain_rate_mmh=rain_rate_mmh,
                    solar_rad_wm2=solar_wm2,
                )
            )
        else:
            canopy_vpd_kpa = None
            vpd_stress_state = "unknown"
            vpd_stress_note = "Waiting for temperature and humidity data."
            block_pollen_ok = False
            block_pollen_score = 0.0
            block_pollen_note = "Waiting for temperature and humidity data."

        sync_status, sync_attrs = evaluate_chill_and_bloom_sync(
            chill_units=self.utah_chill_units,
            primary_target=primary_chill_target,
            secondary_target=secondary_chill_target,
            current_stage=self.phenology_stage,
            species=species,
        )

        if wet_bulb_c is not None and canopy_temp_c is not None:
            frost_risk_level, frost_attrs = evaluate_stage_frost_risk(
                wet_bulb_c=wet_bulb_c,
                canopy_temp_c=canopy_temp_c,
                stage=self.phenology_stage,
                species=species,
            )
        else:
            frost_risk_level = "none"
            frost_attrs = {}

        effective_temp_c = temp_c if temp_c is not None else 15.0
        effective_rh_pct = rh_pct if rh_pct is not None else 60.0

        primary_disease_pct, primary_disease_level, primary_disease_attrs = (
            evaluate_primary_disease_risk(
                species=species,
                lwd_hours=lwd_hours,
                temp_c=effective_temp_c,
                rain_daily_mm=rain_daily_mm,
                stage=self.phenology_stage,
                susceptibility=profile.primary_disease_susceptibility,
            )
        )
        foliar_disease_pct, foliar_disease_level = evaluate_foliar_disease_risk(
            species=species,
            mildew_favorable_hours=mildew_favorable_hours,
            lwd_hours=lwd_hours,
            temp_c=effective_temp_c,
            rh_pct=effective_rh_pct,
            stage=self.phenology_stage,
            susceptibility=profile.foliar_disease_susceptibility,
        )
        rot_disease_pct, rot_disease_level = evaluate_rot_or_desiccation_risk(
            species=species,
            lwd_hours=lwd_hours,
            temp_c=effective_temp_c,
            rh_pct=effective_rh_pct,
            solar_rad_wm2=solar_wm2,
            wind_speed_ms=wind_ms,
            soil_temp_c=soil_temp_c,
            stage=self.phenology_stage,
        )

        early_pest_status, early_pest_risk_pct, early_pest_note = (
            evaluate_early_pest_status(
                species=species,
                gdd_6c=self.gdd_6c,
                stage=self.phenology_stage,
                susceptibility=profile.pest_susceptibility,
            )
        )
        mid_pest_status, mid_pest_risk_pct, mid_pest_note = (
            evaluate_mid_pest_status(
                species=species,
                gdd_7c=self.gdd_7c,
                air_temp_c=effective_temp_c,
                soil_temp_c=soil_temp_c,
                canopy_vpd_kpa=canopy_vpd_kpa,
                stage=self.phenology_stage,
            )
        )
        late_pest_status, late_pest_risk_pct, late_pest_note = (
            evaluate_late_pest_status(
                species=species,
                gdd_10c=self.gdd_10c,
                stage=self.phenology_stage,
            )
        )

        self._schedule_save()

        return {
            "profile_key": profile.key,
            "species": profile.species,
            "species_label": profile.species_label,
            "profile_name": profile.name,
            "pollination_type": profile.pollination_type,
            "phenology_stage": self.phenology_stage,
            "auto_stage_enabled": self.auto_stage_enabled,
            "chill_hours": round(self.chill_hours, 1),
            "utah_chill_units": round(self.utah_chill_units, 1),
            "primary_chill_target": primary_chill_target,
            "secondary_chill_target": secondary_chill_target,
            "primary_chill_pct": sync_attrs["primary_chill_fulfillment_pct"],
            "secondary_chill_pct": sync_attrs["secondary_chill_fulfillment_pct"],
            "bloom_sync_status": sync_status,
            "bloom_sync_attrs": sync_attrs,
            "pollination_window_favorable": block_pollen_ok,
            "pollination_window_score": block_pollen_score,
            "pollination_window_note": block_pollen_note,
            "gdd_custom": round(self.gdd_custom, 1),
            "gdd_base_c": gdd_base_c,
            "gdd_upper_c": gdd_upper_c,
            "gdd_6c": round(self.gdd_6c, 1),
            "gdd_7c": round(self.gdd_7c, 1),
            "gdd_10c": round(self.gdd_10c, 1),
            "canopy_temp_c": canopy_temp_c,
            "canopy_temp_source": (
                "measured" if measured_canopy_temp_c is not None else "modeled"
            ),
            "canopy_vpd_kpa": canopy_vpd_kpa,
            "vpd_stress_state": vpd_stress_state,
            "vpd_stress_note": vpd_stress_note,
            "vpd_optimal_range_kpa": f"0.35 - {profile.vpd_optimal_max_kpa} kPa",
            "kc": kc,
            "etc_daily_mm": round(self.etc_daily_mm, 2),
            "etc_yesterday_mm": round(self.etc_yesterday_mm, 2),
            "canopy_area_m2": canopy_area_m2,
            "plants_count": plants_count,
            "daily_plant_liters": daily_plant_liters,
            "daily_block_liters": daily_block_liters,
            "water_deficit_mm": round(self.water_deficit_mm, 2),
            "taw_mm": taw_mm,
            "raw_threshold_mm": raw_threshold_mm,
            "mad_pct": round(profile.mad_fraction * 100.0, 0),
            "root_zone_depletion_pct": depletion_pct,
            "soil_moisture_avg_pct": soil_moisture_avg_pct,
            "soil_temp_c": soil_temp_c,
            "irrigation_needed": irrigation_needed,
            "recommended_irrigation_liters_per_plant": recommended_irrigation_liters_per_plant,
            "last_irrigation_ts": self.last_irrigation_ts,
            "last_irrigation_mm": self.last_irrigation_mm,
            "frost_risk_level": frost_risk_level,
            "frost_attrs": frost_attrs,
            "primary_disease_name": profile.primary_disease_name,
            "primary_disease_pct": primary_disease_pct,
            "primary_disease_level": primary_disease_level,
            "primary_disease_attrs": primary_disease_attrs,
            "foliar_disease_name": profile.foliar_disease_name,
            "foliar_disease_pct": foliar_disease_pct,
            "foliar_disease_level": foliar_disease_level,
            "rot_disease_name": profile.rot_disease_name,
            "rot_disease_pct": rot_disease_pct,
            "rot_disease_level": rot_disease_level,
            "early_pest_name": profile.early_pest_name,
            "early_pest_status": early_pest_status,
            "early_pest_risk_pct": early_pest_risk_pct,
            "early_pest_note": early_pest_note,
            "mid_pest_name": profile.mid_pest_name,
            "mid_pest_status": mid_pest_status,
            "mid_pest_risk_pct": mid_pest_risk_pct,
            "mid_pest_note": mid_pest_note,
            "late_pest_name": profile.late_pest_name,
            "late_pest_status": late_pest_status,
            "late_pest_risk_pct": late_pest_risk_pct,
            "late_pest_note": late_pest_note,
        }


OrchardBlockCoordinator = PlantBlockCoordinator
