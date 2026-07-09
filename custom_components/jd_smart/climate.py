"""Climate platform for JD Smart."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JdSmartConfigEntry
from .entity import JdSmartEntity

MODE_TO_HVAC = {
    "0": HVACMode.COOL,
    "1": HVACMode.HEAT,
    "2": HVACMode.DRY,
    "3": HVACMode.FAN_ONLY,
    "4": HVACMode.AUTO,
}
HVAC_TO_MODE = {value: key for key, value in MODE_TO_HVAC.items()}

YAIR_MODE_TO_HVAC = {
    "0": HVACMode.AUTO,
    "1": HVACMode.COOL,
    "2": HVACMode.DRY,
    "3": HVACMode.FAN_ONLY,
    "4": HVACMode.HEAT,
}
YAIR_HVAC_TO_MODE = {value: key for key, value in YAIR_MODE_TO_HVAC.items()}

FAN_TO_VALUE = {
    "silent": "0",
    "low": "1",
    "medium": "2",
    "high": "3",
    "auto": "5",
}
VALUE_TO_FAN = {value: key for key, value in FAN_TO_VALUE.items()}

YAIR_FAN_TO_VALUE = {
    "auto": "00",
    "high": "01",
    "medium": "02",
    "low": "03",
}
YAIR_VALUE_TO_FAN = {
    value.removeprefix("0") or "0": key
    for key, value in YAIR_FAN_TO_VALUE.items()
}

SWING_TO_VALUE = {
    "swing": "0",
    "auto": "1",
    "direction_1": "2",
    "direction_2": "3",
    "direction_3": "4",
    "direction_4": "5",
    "direction_5": "6",
    "direction_6": "7",
}
VALUE_TO_SWING = {value: key for key, value in SWING_TO_VALUE.items()}

PRESET_TO_VALUE = {
    "off": "0",
    "normal": "1",
    "elderly": "2",
    "youth": "3",
    "child": "4",
}
VALUE_TO_PRESET = {value: key for key, value in PRESET_TO_VALUE.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JdSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up JD Smart climate."""
    async_add_entities(
        JdSmartClimate(coordinator)
        for coordinator in entry.runtime_data.coordinators.values()
    )


class JdSmartClimate(JdSmartEntity, ClimateEntity):
    """JD Smart climate entity."""

    _attr_name = None
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 18
    _attr_max_temp = 32
    _attr_target_temperature_step = 1
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.AUTO,
    ]
    _attr_fan_modes = list(FAN_TO_VALUE)
    _attr_preset_modes = list(PRESET_TO_VALUE)
    _attr_swing_modes = list(SWING_TO_VALUE)
    _attr_translation_key = "air_conditioner"

    def __init__(self, coordinator) -> None:
        """Initialize climate."""
        super().__init__(coordinator, "climate")

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature."""
        return _float_or_none(
            self.streams.get("curtemp") or self.streams.get("indoor_temperature")
        )

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        return _temperature_or_none(
            self.streams.get("settemp") or self.streams.get("temperature")
        )

    @property
    def current_humidity(self) -> float | None:
        """Return current humidity."""
        return _float_or_none(self.streams.get("curhum"))

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return HVAC mode."""
        if self._uses_yair_streams:
            if self.streams.get("state") == "0":
                return HVACMode.OFF
            return YAIR_MODE_TO_HVAC.get(self.streams.get("model", ""))
        if self.streams.get("power") == "0":
            return HVACMode.OFF
        return MODE_TO_HVAC.get(self.streams.get("mode", ""))

    @property
    def fan_mode(self) -> str | None:
        """Return fan mode."""
        if self._uses_yair_streams:
            return YAIR_VALUE_TO_FAN.get(self.streams.get("wind_speed", ""))
        return VALUE_TO_FAN.get(
            self.streams.get("mark") or self.streams.get("wind_speed", "")
        )

    @property
    def fan_modes(self) -> list[str]:
        """Return available fan modes."""
        if self._uses_yair_streams:
            return list(YAIR_FAN_TO_VALUE)
        return list(FAN_TO_VALUE)

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return supported features."""
        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.SWING_MODE
        )
        if not self._uses_yair_streams:
            features |= ClimateEntityFeature.PRESET_MODE
        return features

    @property
    def swing_mode(self) -> str | None:
        """Return swing mode."""
        return VALUE_TO_SWING.get(
            self.streams.get("verdir")
            or self.streams.get("wind_orientation_vertical", "")
        )

    @property
    def preset_mode(self) -> str | None:
        """Return preset mode."""
        if self._uses_yair_streams:
            return None
        return VALUE_TO_PRESET.get(self.streams.get("sleepmode", ""))

    @property
    def preset_modes(self) -> list[str] | None:
        """Return preset modes."""
        if self._uses_yair_streams:
            return None
        return list(PRESET_TO_VALUE)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        if self._uses_yair_streams:
            await self._control({"setTemperature": int(temperature)})
            return
        await self._control({"settemp": int(temperature)})

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if self._uses_yair_streams:
            if hvac_mode == HVACMode.OFF:
                await self._control({"setSwitch": "false"})
                return
            mode = YAIR_HVAC_TO_MODE[hvac_mode]
            if self.streams.get("state") == "0":
                await self._control({"setSwitch": "true"})
            await self._control({"setModel": mode.zfill(2)})
            return
        if hvac_mode == HVACMode.OFF:
            await self._control({"power": 0})
            return
        mode = HVAC_TO_MODE[hvac_mode]
        await self._control({"power": 1, "mode": int(mode)})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        if self._uses_yair_streams:
            await self._control({"setWindSpeed": YAIR_FAN_TO_VALUE[fan_mode]})
            return
        await self._control({"mark": int(FAN_TO_VALUE[fan_mode])})

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set swing mode."""
        if self._uses_yair_streams:
            await self._control(
                {
                    "setUpOrDown": SWING_TO_VALUE[swing_mode].zfill(2),
                    "mapTTData": "type:1:int",
                }
            )
            return
        await self._control({"verdir": int(SWING_TO_VALUE[swing_mode])})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        if self._uses_yair_streams:
            raise HomeAssistantError("Preset mode is not supported by this device")
        await self._control({"sleepmode": int(PRESET_TO_VALUE[preset_mode])})

    async def _control(self, commands: dict[str, object]) -> None:
        """Control helper."""
        try:
            await self.coordinator.async_control_streams(commands)
        except Exception as err:
            raise HomeAssistantError("Unable to control JD Smart") from err

    @property
    def _uses_yair_streams(self) -> bool:
        """Return whether the current snapshot uses Yair stream names."""
        return any(
            stream_id in self.streams
            for stream_id in (
                "state",
                "model",
                "temperature",
                "wind_speed",
            )
        )


def _float_or_none(value: str | None) -> float | None:
    """Convert a value to float."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _temperature_or_none(value: str | None) -> float | None:
    """Convert a temperature stream value to float."""
    if value is None:
        return None
    return _float_or_none(value.removesuffix("°C"))
