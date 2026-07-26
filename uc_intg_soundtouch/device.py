"""Bose SoundTouch speaker device (WebSocket push + polling fallback)."""

import asyncio
import logging
from typing import Any
from xml.etree import ElementTree as ET

import aiohttp

from ucapi_framework import WebSocketPollingDevice

from uc_intg_soundtouch.client import (
    SoundTouchClient,
    parse_now_playing,
    parse_presets,
    parse_sources,
    parse_volume,
)
from uc_intg_soundtouch.config import SoundTouchConfig
from uc_intg_soundtouch.const import (
    KEY_MUTE,
    KEY_NEXT_TRACK,
    KEY_PAUSE,
    KEY_PLAY,
    KEY_PLAY_PAUSE,
    KEY_POWER,
    KEY_PREV_TRACK,
    KEY_STOP,
    KEY_VOLUME_DOWN,
    KEY_VOLUME_UP,
    PLAY_STATUS_MAP,
    PRESET_KEYS,
    SOURCE_AUX,
    SOURCE_BLUETOOTH,
    SOURCE_STANDBY,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)

_LOG = logging.getLogger(__name__)

_SELECTABLE_SOURCES = {SOURCE_AUX, SOURCE_BLUETOOTH}


class SoundTouchDevice(WebSocketPollingDevice):
    """One Bose SoundTouch speaker."""

    def __init__(self, device_config: SoundTouchConfig, **kwargs: Any) -> None:
        super().__init__(
            device_config,
            poll_interval=30,
            ping_interval=0,  # aiohttp ws heartbeat handles keepalive
            **kwargs,
        )
        self._device_config = device_config
        self._client = SoundTouchClient(
            device_config.host, device_config.api_port, device_config.ws_port
        )
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._state: str = STATE_UNAVAILABLE
        self._info: dict[str, Any] = {}
        self._now_playing: dict[str, Any] = {}
        self._volume: dict[str, Any] = {"actual": 0, "target": 0, "muted": False}
        self._presets: list[dict[str, Any]] = []
        self._sources: list[dict[str, Any]] = []

    # -- identity ------------------------------------------------------
    @property
    def identifier(self) -> str:
        return self._device_config.identifier

    @property
    def name(self) -> str:
        return self._device_config.name

    @property
    def address(self) -> str:
        return self._device_config.host

    @property
    def log_id(self) -> str:
        return f"{self.name} ({self.address})"

    @property
    def state(self) -> str:
        return self._state

    @property
    def available(self) -> bool:
        return self._state != STATE_UNAVAILABLE

    @property
    def client(self) -> SoundTouchClient:
        return self._client

    # -- state accessors used by entities ------------------------------
    @property
    def power(self) -> bool:
        source = self._now_playing.get("source", "")
        return bool(source) and source != SOURCE_STANDBY

    @property
    def volume(self) -> int:
        return int(self._volume.get("actual", 0))

    @property
    def muted(self) -> bool:
        return bool(self._volume.get("muted", False))

    @property
    def source(self) -> str:
        source = self._now_playing.get("source", "")
        return "" if source in ("", SOURCE_STANDBY) else self._display_name_for(source)

    @property
    def source_list(self) -> list[str]:
        names = [
            s["display_name"] or s["source"]
            for s in self._sources
            if s["source"] in _SELECTABLE_SOURCES and s["status"] == "READY"
        ]
        return names

    @property
    def media_title(self) -> str:
        return self._now_playing.get("track") or self._now_playing.get("station_name", "")

    @property
    def media_artist(self) -> str:
        return self._now_playing.get("artist", "")

    @property
    def media_album(self) -> str:
        return self._now_playing.get("album", "")

    @property
    def media_image_url(self) -> str:
        if self._now_playing.get("art_status") == "IMAGE_PRESENT":
            return self._now_playing.get("art_url", "")
        return ""

    @property
    def presets(self) -> list[dict[str, Any]]:
        return list(self._presets)

    @property
    def info(self) -> dict[str, Any]:
        return dict(self._info)

    def _display_name_for(self, source: str) -> str:
        for item in self._sources:
            if item["source"] == source:
                return item["display_name"] or source
        return source

    def _source_from_display(self, display: str) -> tuple[str, str] | None:
        for item in self._sources:
            name = item["display_name"] or item["source"]
            if name.lower() == display.lower() or item["source"].lower() == display.lower():
                return item["source"], item["source_account"]
        return None

    # -- commands ------------------------------------------------------
    async def power_on(self) -> None:
        if not self.power:
            await self._client.send_key(KEY_POWER)

    async def power_off(self) -> None:
        if self.power:
            await self._client.send_key(KEY_POWER)

    async def toggle_power(self) -> None:
        await self._client.send_key(KEY_POWER)

    async def play(self) -> None:
        await self._client.send_key(KEY_PLAY)

    async def pause(self) -> None:
        await self._client.send_key(KEY_PAUSE)

    async def play_pause(self) -> None:
        await self._client.send_key(KEY_PLAY_PAUSE)

    async def stop(self) -> None:
        await self._client.send_key(KEY_STOP)

    async def next_track(self) -> None:
        await self._client.send_key(KEY_NEXT_TRACK)

    async def previous_track(self) -> None:
        await self._client.send_key(KEY_PREV_TRACK)

    async def volume_up(self) -> None:
        await self._client.send_key(KEY_VOLUME_UP)

    async def volume_down(self) -> None:
        await self._client.send_key(KEY_VOLUME_DOWN)

    async def set_volume(self, level: int) -> None:
        await self._client.set_volume(level)

    async def mute_toggle(self) -> None:
        await self._client.send_key(KEY_MUTE)

    async def set_mute(self, mute: bool) -> None:
        if mute != self.muted:
            await self._client.send_key(KEY_MUTE)

    async def select_source(self, display: str) -> bool:
        match = self._source_from_display(display)
        if not match:
            _LOG.warning("[%s] Unknown source: %s", self.log_id, display)
            return False
        source, account = match
        await self._client.select_source(source, account)
        return True

    async def select_preset(self, preset_id: int) -> bool:
        key = PRESET_KEYS.get(int(preset_id))
        if not key:
            return False
        await self._client.send_key(key)
        return True

    async def send_key(self, key: str) -> None:
        await self._client.send_key(key)

    # -- state application ---------------------------------------------
    def _recompute_state(self) -> None:
        source = self._now_playing.get("source", "")
        if not source or source == SOURCE_STANDBY:
            self._state = STATE_OFF
            return
        self._state = PLAY_STATUS_MAP.get(self._now_playing.get("play_status", ""), STATE_ON)

    async def _seed_state(self) -> None:
        self._info = await self._client.get_info()
        self._now_playing = await self._client.get_now_playing()
        self._volume = await self._client.get_volume()
        self._presets = await self._client.get_presets()
        self._sources = await self._client.get_sources()
        self._recompute_state()

    # -- WebSocket -----------------------------------------------------
    async def create_websocket(self) -> Any:
        self._ws = await self._client.ws_connect()
        return self._ws

    async def close_websocket(self) -> None:
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    async def receive_message(self) -> Any:
        msg = await self._ws.receive()
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                return ET.fromstring(msg.data)
            except ET.ParseError:
                return {}
        if msg.type in (
            aiohttp.WSMsgType.CLOSED,
            aiohttp.WSMsgType.CLOSING,
            aiohttp.WSMsgType.ERROR,
        ):
            return None
        return {}

    async def handle_message(self, message: Any) -> None:
        if not isinstance(message, ET.Element):
            return
        if message.tag != "updates":
            return
        changed = False
        for event in list(message):
            if event.tag == "nowPlayingUpdated":
                node = event.find("nowPlaying")
                if node is not None:
                    self._now_playing = parse_now_playing(node)
                    self._recompute_state()
                    changed = True
            elif event.tag == "volumeUpdated":
                node = event.find("volume")
                if node is not None:
                    self._volume = parse_volume(node)
                    changed = True
            elif event.tag == "presetsUpdated":
                node = event.find("presets")
                if node is not None:
                    self._presets = parse_presets(node)
                    changed = True
            elif event.tag == "sourcesUpdated":
                try:
                    self._sources = await self._client.get_sources()
                    changed = True
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
        if changed:
            self.push_update()

    # -- Polling fallback ----------------------------------------------
    async def establish_connection(self) -> None:
        async with self._connect_lock:
            try:
                await self._seed_state()
            except Exception as err:  # pylint: disable=broad-exception-caught
                self._state = STATE_UNAVAILABLE
                raise ConnectionError(f"Cannot reach SoundTouch at {self.address}") from err
        self.push_update()

    async def poll_device(self) -> None:
        try:
            self._now_playing = await self._client.get_now_playing()
            self._volume = await self._client.get_volume()
            self._recompute_state()
            self.push_update()
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.debug("[%s] Poll failed: %s", self.log_id, err)
            if self._state != STATE_UNAVAILABLE and not self.is_connected:
                self._state = STATE_UNAVAILABLE
                self.push_update()

    # -- lifecycle -----------------------------------------------------
    async def disconnect(self, stop_polling: bool | None = None) -> None:
        await super().disconnect(stop_polling=stop_polling)
        if stop_polling:
            await self._client.close()
            self._state = STATE_UNAVAILABLE
