"""Integration driver for Bose SoundTouch."""

from ucapi_framework import BaseIntegrationDriver

from uc_intg_soundtouch.config import SoundTouchConfig
from uc_intg_soundtouch.device import SoundTouchDevice
from uc_intg_soundtouch.media_player import create_media_player
from uc_intg_soundtouch.remote import create_remote
from uc_intg_soundtouch.select import create_selects
from uc_intg_soundtouch.sensor import create_sensors


class SoundTouchDriver(BaseIntegrationDriver[SoundTouchDevice, SoundTouchConfig]):
    """Builds a media_player, remote, preset select, and sensors per speaker."""

    def __init__(self) -> None:
        super().__init__(
            device_class=SoundTouchDevice,
            entity_classes=[
                create_media_player,
                create_remote,
                create_selects,
                create_sensors,
            ],
            driver_id="uc_intg_soundtouch",
        )
