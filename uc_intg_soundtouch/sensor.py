"""Bose SoundTouch sensors: current source and now-playing text."""

import logging

from ucapi import sensor
from ucapi_framework import SensorEntity

from uc_intg_soundtouch.config import SoundTouchConfig
from uc_intg_soundtouch.const import STATE_OFF
from uc_intg_soundtouch.device import SoundTouchDevice

_LOG = logging.getLogger(__name__)


class SoundTouchSourceSensor(SensorEntity):
    """Shows the currently selected source (or Standby)."""

    def __init__(self, device_config: SoundTouchConfig, device: SoundTouchDevice) -> None:
        self._device = device
        entity_id = f"sensor.{device_config.identifier}.source"
        super().__init__(
            entity_id,
            f"{device_config.name} Source",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: ""},
            device_class=sensor.DeviceClasses.CUSTOM,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if not self._device.available:
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        value = "Standby" if self._device.state == STATE_OFF else (self._device.source or "Idle")
        self.update({sensor.Attributes.STATE: sensor.States.ON, sensor.Attributes.VALUE: value})


class SoundTouchNowPlayingSensor(SensorEntity):
    """Shows the current track / station text."""

    def __init__(self, device_config: SoundTouchConfig, device: SoundTouchDevice) -> None:
        self._device = device
        entity_id = f"sensor.{device_config.identifier}.now_playing"
        super().__init__(
            entity_id,
            f"{device_config.name} Now Playing",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: ""},
            device_class=sensor.DeviceClasses.CUSTOM,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if not self._device.available:
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        if self._device.state == STATE_OFF:
            value = "Off"
        else:
            title = self._device.media_title
            artist = self._device.media_artist
            value = f"{artist} - {title}" if artist and title else (title or "Nothing playing")
        self.update({sensor.Attributes.STATE: sensor.States.ON, sensor.Attributes.VALUE: value})


def create_sensors(device_config: SoundTouchConfig, device: SoundTouchDevice) -> list[SensorEntity]:
    return [
        SoundTouchSourceSensor(device_config, device),
        SoundTouchNowPlayingSensor(device_config, device),
    ]
