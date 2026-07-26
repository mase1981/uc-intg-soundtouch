"""Configuration dataclass and manager for the Bose SoundTouch integration."""

from dataclasses import dataclass

from ucapi_framework import BaseConfigManager

from uc_intg_soundtouch.const import DEFAULT_API_PORT, DEFAULT_WS_PORT


@dataclass
class SoundTouchConfig:
    """Configuration for a single Bose SoundTouch speaker."""

    identifier: str = ""
    name: str = ""
    host: str = ""
    api_port: int = DEFAULT_API_PORT
    ws_port: int = DEFAULT_WS_PORT

    def __post_init__(self) -> None:
        try:
            self.api_port = int(self.api_port)
        except (TypeError, ValueError):
            self.api_port = DEFAULT_API_PORT
        try:
            self.ws_port = int(self.ws_port)
        except (TypeError, ValueError):
            self.ws_port = DEFAULT_WS_PORT


class SoundTouchConfigManager(BaseConfigManager[SoundTouchConfig]):
    """Config manager bound to :class:`SoundTouchConfig`."""
