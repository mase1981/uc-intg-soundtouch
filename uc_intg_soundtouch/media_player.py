"""Bose SoundTouch media_player entity."""

import logging
from typing import Any

from ucapi import StatusCodes, media_player
from ucapi.media_player import MediaContentType
from ucapi_framework import MediaPlayerEntity

from uc_intg_soundtouch.config import SoundTouchConfig
from uc_intg_soundtouch.const import STATE_OFF, STATE_PAUSED, STATE_PLAYING
from uc_intg_soundtouch.device import SoundTouchDevice

_LOG = logging.getLogger(__name__)

FEATURES = [
    media_player.Features.ON_OFF,
    media_player.Features.TOGGLE,
    media_player.Features.VOLUME,
    media_player.Features.VOLUME_UP_DOWN,
    media_player.Features.MUTE_TOGGLE,
    media_player.Features.MUTE,
    media_player.Features.UNMUTE,
    media_player.Features.PLAY_PAUSE,
    media_player.Features.STOP,
    media_player.Features.NEXT,
    media_player.Features.PREVIOUS,
    media_player.Features.MEDIA_TITLE,
    media_player.Features.MEDIA_ARTIST,
    media_player.Features.MEDIA_ALBUM,
    media_player.Features.MEDIA_IMAGE_URL,
    media_player.Features.MEDIA_TYPE,
    media_player.Features.SELECT_SOURCE,
]

_STATE_MAP = {
    STATE_PLAYING: media_player.States.PLAYING,
    STATE_PAUSED: media_player.States.PAUSED,
    STATE_OFF: media_player.States.OFF,
}


class SoundTouchMediaPlayer(MediaPlayerEntity):
    """Full media player for a Bose SoundTouch speaker."""

    def __init__(self, device_config: SoundTouchConfig, device: SoundTouchDevice) -> None:
        self._device = device
        entity_id = f"media_player.{device_config.identifier}"
        super().__init__(
            entity_id,
            device_config.name,
            FEATURES,
            {
                media_player.Attributes.STATE: media_player.States.UNKNOWN,
                media_player.Attributes.VOLUME: 0,
                media_player.Attributes.MUTED: False,
                media_player.Attributes.SOURCE: "",
                media_player.Attributes.SOURCE_LIST: [],
                media_player.Attributes.MEDIA_TITLE: "",
                media_player.Attributes.MEDIA_ARTIST: "",
                media_player.Attributes.MEDIA_ALBUM: "",
                media_player.Attributes.MEDIA_IMAGE_URL: "",
            },
            device_class=media_player.DeviceClasses.SPEAKER,
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if not self._device.available:
            self.update({media_player.Attributes.STATE: media_player.States.UNAVAILABLE})
            return
        state = _STATE_MAP.get(self._device.state, media_player.States.ON)
        playing = state in (media_player.States.PLAYING, media_player.States.PAUSED)
        self.update({
            media_player.Attributes.STATE: state,
            media_player.Attributes.VOLUME: self._device.volume,
            media_player.Attributes.MUTED: self._device.muted,
            media_player.Attributes.SOURCE: self._device.source,
            media_player.Attributes.SOURCE_LIST: self._device.source_list,
            media_player.Attributes.MEDIA_TITLE: self._device.media_title,
            media_player.Attributes.MEDIA_ARTIST: self._device.media_artist,
            media_player.Attributes.MEDIA_ALBUM: self._device.media_album,
            media_player.Attributes.MEDIA_IMAGE_URL: self._device.media_image_url,
            media_player.Attributes.MEDIA_TYPE: MediaContentType.MUSIC if playing else "",
        })

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        try:
            match cmd_id:
                case media_player.Commands.ON:
                    await self._device.power_on()
                case media_player.Commands.OFF:
                    await self._device.power_off()
                case media_player.Commands.TOGGLE:
                    await self._device.toggle_power()
                case media_player.Commands.PLAY_PAUSE:
                    await self._device.play_pause()
                case media_player.Commands.STOP:
                    await self._device.stop()
                case media_player.Commands.NEXT:
                    await self._device.next_track()
                case media_player.Commands.PREVIOUS:
                    await self._device.previous_track()
                case media_player.Commands.VOLUME:
                    await self._device.set_volume(int((params or {}).get("volume", 0)))
                case media_player.Commands.VOLUME_UP:
                    await self._device.volume_up()
                case media_player.Commands.VOLUME_DOWN:
                    await self._device.volume_down()
                case media_player.Commands.MUTE_TOGGLE:
                    await self._device.mute_toggle()
                case media_player.Commands.MUTE:
                    await self._device.set_mute(True)
                case media_player.Commands.UNMUTE:
                    await self._device.set_mute(False)
                case media_player.Commands.SELECT_SOURCE:
                    source = (params or {}).get("source", "")
                    if not await self._device.select_source(source):
                        return StatusCodes.BAD_REQUEST
                case _:
                    return StatusCodes.NOT_IMPLEMENTED
            return StatusCodes.OK
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Command error (%s): %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR


def create_media_player(device_config: SoundTouchConfig, device: SoundTouchDevice) -> list[SoundTouchMediaPlayer]:
    return [SoundTouchMediaPlayer(device_config, device)]
