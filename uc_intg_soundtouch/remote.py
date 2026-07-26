"""Bose SoundTouch remote entity (transport, presets, sources for activities)."""

import logging
from typing import Any

from ucapi import StatusCodes, remote
from ucapi.ui import Buttons, Size, UiPage, create_btn_mapping, create_ui_icon, create_ui_text
from ucapi_framework import RemoteEntity

from uc_intg_soundtouch.config import SoundTouchConfig
from uc_intg_soundtouch.const import (
    KEY_ADD_FAVORITE,
    KEY_NEXT_TRACK,
    KEY_PAUSE,
    KEY_PLAY,
    KEY_PREV_TRACK,
    KEY_REMOVE_FAVORITE,
    KEY_REPEAT_ALL,
    KEY_REPEAT_OFF,
    KEY_REPEAT_ONE,
    KEY_SHUFFLE_OFF,
    KEY_SHUFFLE_ON,
    KEY_STOP,
    KEY_THUMBS_DOWN,
    KEY_THUMBS_UP,
    SOURCE_AUX,
    SOURCE_BLUETOOTH,
)
from uc_intg_soundtouch.device import SoundTouchDevice

_LOG = logging.getLogger(__name__)

SIMPLE_COMMANDS = [
    "POWER", "POWER_ON", "POWER_OFF",
    "PLAY", "PAUSE", "PLAY_PAUSE", "STOP", "NEXT", "PREVIOUS",
    "VOLUME_UP", "VOLUME_DOWN", "MUTE",
    "SHUFFLE_ON", "SHUFFLE_OFF", "REPEAT_ONE", "REPEAT_ALL", "REPEAT_OFF",
    "THUMBS_UP", "THUMBS_DOWN", "ADD_FAVORITE", "REMOVE_FAVORITE",
    "PRESET_1", "PRESET_2", "PRESET_3", "PRESET_4", "PRESET_5", "PRESET_6",
    "SOURCE_AUX", "SOURCE_BLUETOOTH",
]

_RAW_KEYS = {
    "PLAY": KEY_PLAY,
    "PAUSE": KEY_PAUSE,
    "STOP": KEY_STOP,
    "NEXT": KEY_NEXT_TRACK,
    "PREVIOUS": KEY_PREV_TRACK,
    "SHUFFLE_ON": KEY_SHUFFLE_ON,
    "SHUFFLE_OFF": KEY_SHUFFLE_OFF,
    "REPEAT_ONE": KEY_REPEAT_ONE,
    "REPEAT_ALL": KEY_REPEAT_ALL,
    "REPEAT_OFF": KEY_REPEAT_OFF,
    "THUMBS_UP": KEY_THUMBS_UP,
    "THUMBS_DOWN": KEY_THUMBS_DOWN,
    "ADD_FAVORITE": KEY_ADD_FAVORITE,
    "REMOVE_FAVORITE": KEY_REMOVE_FAVORITE,
}


class SoundTouchRemote(RemoteEntity):
    """Exposes SoundTouch keys as simple commands usable in activities."""

    def __init__(self, device_config: SoundTouchConfig, device: SoundTouchDevice) -> None:
        self._device = device
        entity_id = f"remote.{device_config.identifier}"
        super().__init__(
            entity_id,
            f"{device_config.name} Remote",
            [remote.Features.ON_OFF, remote.Features.TOGGLE, remote.Features.SEND_CMD],
            {remote.Attributes.STATE: remote.States.UNKNOWN},
            simple_commands=SIMPLE_COMMANDS,
            button_mapping=[
                create_btn_mapping(Buttons.DPAD_MIDDLE, short="PLAY_PAUSE"),
                create_btn_mapping(Buttons.PREV, short="PREVIOUS"),
                create_btn_mapping(Buttons.NEXT, short="NEXT"),
                create_btn_mapping(Buttons.PLAY, short="PLAY_PAUSE"),
                create_btn_mapping(Buttons.VOLUME_UP, short="VOLUME_UP"),
                create_btn_mapping(Buttons.VOLUME_DOWN, short="VOLUME_DOWN"),
                create_btn_mapping(Buttons.MUTE, short="MUTE"),
                create_btn_mapping(Buttons.POWER, short="POWER"),
            ],
            ui_pages=[
                UiPage("presets", "Presets", grid=Size(4, 6), items=[
                    create_ui_text("Preset 1", 0, 0, cmd="PRESET_1"),
                    create_ui_text("Preset 2", 2, 0, cmd="PRESET_2"),
                    create_ui_text("Preset 3", 0, 1, cmd="PRESET_3"),
                    create_ui_text("Preset 4", 2, 1, cmd="PRESET_4"),
                    create_ui_text("Preset 5", 0, 2, cmd="PRESET_5"),
                    create_ui_text("Preset 6", 2, 2, cmd="PRESET_6"),
                    create_ui_text("AUX", 0, 3, cmd="SOURCE_AUX"),
                    create_ui_text("Bluetooth", 2, 3, cmd="SOURCE_BLUETOOTH"),
                    create_ui_icon("uc:play", 0, 4, cmd="PLAY_PAUSE"),
                    create_ui_icon("uc:stop", 1, 4, cmd="STOP"),
                    create_ui_icon("uc:bw", 2, 4, cmd="PREVIOUS"),
                    create_ui_icon("uc:ff", 3, 4, cmd="NEXT"),
                    create_ui_icon("uc:power-on", 0, 5, cmd="POWER_ON"),
                    create_ui_icon("uc:power-off", 1, 5, cmd="POWER_OFF"),
                    create_ui_icon("uc:mute", 2, 5, cmd="MUTE"),
                ]),
            ],
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if not self._device.available:
            self.update({remote.Attributes.STATE: remote.States.UNAVAILABLE})
            return
        self.update({
            remote.Attributes.STATE: remote.States.ON if self._device.power else remote.States.OFF,
        })

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        try:
            if cmd_id == remote.Commands.ON:
                await self._device.power_on()
                return StatusCodes.OK
            if cmd_id == remote.Commands.OFF:
                await self._device.power_off()
                return StatusCodes.OK
            if cmd_id == remote.Commands.TOGGLE:
                await self._device.toggle_power()
                return StatusCodes.OK
            if cmd_id != remote.Commands.SEND_CMD:
                return StatusCodes.NOT_IMPLEMENTED
            command = (params or {}).get("command", "")
            return await self._run(command)
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Remote command error (%s): %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    async def _run(self, command: str) -> StatusCodes:
        if command == "POWER":
            await self._device.toggle_power()
        elif command == "POWER_ON":
            await self._device.power_on()
        elif command == "POWER_OFF":
            await self._device.power_off()
        elif command == "PLAY_PAUSE":
            await self._device.play_pause()
        elif command == "VOLUME_UP":
            await self._device.volume_up()
        elif command == "VOLUME_DOWN":
            await self._device.volume_down()
        elif command == "MUTE":
            await self._device.mute_toggle()
        elif command == "SOURCE_AUX":
            await self._device.client.select_source(SOURCE_AUX)
        elif command == "SOURCE_BLUETOOTH":
            await self._device.client.select_source(SOURCE_BLUETOOTH)
        elif command.startswith("PRESET_"):
            await self._device.select_preset(int(command.split("_")[1]))
        elif command in _RAW_KEYS:
            await self._device.send_key(_RAW_KEYS[command])
        else:
            return StatusCodes.NOT_IMPLEMENTED
        return StatusCodes.OK


def create_remote(device_config: SoundTouchConfig, device: SoundTouchDevice) -> list[SoundTouchRemote]:
    return [SoundTouchRemote(device_config, device)]
