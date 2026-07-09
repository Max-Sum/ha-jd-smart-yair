"""Select platform for JD Smart."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JdSmartConfigEntry
from .entity import JdSmartEntity

YAIR_HORIZONTAL_OPTION_TO_VALUE = {"swing": "06", "direct": "00"}
YAIR_HORIZONTAL_VALUE_TO_OPTION = {"6": "swing", "0": "direct"}


@dataclass(frozen=True, kw_only=True)
class JdSmartSelectDescription(SelectEntityDescription):
    """JD Smart select description."""

    stream_id: str
    option_to_value: dict[str, str]


SELECTS: tuple[JdSmartSelectDescription, ...] = (
    JdSmartSelectDescription(
        key="hordir",
        stream_id="hordir",
        translation_key="horizontal_direction",
        options=["swing", "direct"],
        option_to_value={"swing": "0", "direct": "1"},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JdSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up JD Smart selects."""
    async_add_entities(
        JdSmartSelect(coordinator, description)
        for coordinator in entry.runtime_data.coordinators.values()
        for description in SELECTS
    )


class JdSmartSelect(JdSmartEntity, SelectEntity):
    """JD Smart stream select."""

    entity_description: JdSmartSelectDescription

    def __init__(
        self,
        coordinator,
        description: JdSmartSelectDescription,
    ) -> None:
        """Initialize select."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key
        self._value_to_option = {
            value: option for option, value in description.option_to_value.items()
        }

    @property
    def current_option(self) -> str | None:
        """Return selected option."""
        if self._uses_yair_streams:
            return YAIR_HORIZONTAL_VALUE_TO_OPTION.get(
                self.streams.get("wind_orientation_horizontal", "")
            )
        return self._value_to_option.get(
            self.streams.get(self.entity_description.stream_id, "")
        )

    async def async_select_option(self, option: str) -> None:
        """Select option."""
        try:
            if self._uses_yair_streams:
                await self.coordinator.async_control_streams(
                    {
                        "setLeftOrRight": YAIR_HORIZONTAL_OPTION_TO_VALUE[option],
                        "mapTTData": "type:0:int",
                    }
                )
                return
            await self.coordinator.async_control_streams(
                {
                    self.entity_description.stream_id: int(
                        self.entity_description.option_to_value[option]
                    )
                }
            )
        except Exception as err:
            raise HomeAssistantError("Unable to control JD Smart") from err

    @property
    def _uses_yair_streams(self) -> bool:
        """Return whether the current snapshot uses Yair horizontal streams."""
        return "wind_orientation_horizontal" in self.streams
