"""Bose SoundTouch preset Select entity."""

import logging
from typing import Any

from ucapi import StatusCodes, select
from ucapi_framework import SelectEntity

from uc_intg_soundtouch.config import SoundTouchConfig
from uc_intg_soundtouch.device import SoundTouchDevice

_LOG = logging.getLogger(__name__)


class SoundTouchPresetSelect(SelectEntity):
    """Selects one of the speaker's 6 stored presets."""

    def __init__(self, device_config: SoundTouchConfig, device: SoundTouchDevice) -> None:
        self._device = device
        entity_id = f"select.{device_config.identifier}.preset"
        super().__init__(
            entity_id,
            f"{device_config.name} Preset",
            {
                select.Attributes.STATE: select.States.UNKNOWN,
                select.Attributes.OPTIONS: [],
                select.Attributes.CURRENT_OPTION: "",
            },
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    def _options(self) -> list[str]:
        return [f"{p['id']}: {p['name']}" for p in self._device.presets if p.get("name")]

    def _current(self, options: list[str]) -> str:
        playing = self._device.media_title
        for option in options:
            name = option.split(": ", 1)[-1]
            if name and name == playing:
                return option
        return ""

    async def sync_state(self) -> None:
        if not self._device.available:
            self.update({select.Attributes.STATE: select.States.UNAVAILABLE})
            return
        options = self._options()
        self.update({
            select.Attributes.STATE: select.States.ON,
            select.Attributes.OPTIONS: options,
            select.Attributes.CURRENT_OPTION: self._current(options),
        })

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        try:
            if cmd_id != select.Commands.SELECT_OPTION:
                return StatusCodes.NOT_IMPLEMENTED
            option = (params or {}).get("option", "")
            if not option or ":" not in option:
                return StatusCodes.BAD_REQUEST
            preset_id = int(option.split(":", 1)[0].strip())
            if await self._device.select_preset(preset_id):
                return StatusCodes.OK
            return StatusCodes.BAD_REQUEST
        except (ValueError, IndexError) as err:
            _LOG.error("[%s] Preset select error: %s", entity.id, err)
            return StatusCodes.BAD_REQUEST
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Preset select error: %s", entity.id, err)
            return StatusCodes.SERVER_ERROR


def create_selects(device_config: SoundTouchConfig, device: SoundTouchDevice) -> list[SoundTouchPresetSelect]:
    return [SoundTouchPresetSelect(device_config, device)]
