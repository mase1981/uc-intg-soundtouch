"""Async REST + WebSocket client for a Bose SoundTouch speaker.

REST/XML control runs on port 8090; real-time notifications are pushed over a
WebSocket on port 8080 using the ``gabbo`` subprotocol. All payloads are XML;
parsing is done with the standard library (no third-party SoundTouch lib).
"""

import logging
from typing import Any
from xml.etree import ElementTree as ET

import aiohttp

from uc_intg_soundtouch.const import (
    DEFAULT_API_PORT,
    DEFAULT_WS_PORT,
    WS_SENDER,
    WS_SUBPROTOCOL,
)

_LOG = logging.getLogger(__name__)


def _text(element: ET.Element | None, tag: str, default: str = "") -> str:
    if element is None:
        return default
    child = element.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def parse_now_playing(node: ET.Element) -> dict[str, Any]:
    """Parse a <nowPlaying> element into a flat dict."""
    content_item = node.find("ContentItem")
    art = node.find("art")
    return {
        "source": node.get("source", ""),
        "source_account": node.get("sourceAccount", ""),
        "track": _text(node, "track"),
        "artist": _text(node, "artist"),
        "album": _text(node, "album"),
        "station_name": _text(node, "stationName"),
        "description": _text(node, "description"),
        "play_status": _text(node, "playStatus"),
        "art_url": (art.text or "").strip() if art is not None else "",
        "art_status": art.get("artImageStatus", "") if art is not None else "",
        "content_item_name": _text(content_item, "itemName") if content_item is not None else "",
        "content_source": content_item.get("source", "") if content_item is not None else "",
    }


def parse_volume(node: ET.Element) -> dict[str, Any]:
    """Parse a <volume> element into a dict."""
    return {
        "actual": int(_text(node, "actualvolume", "0") or 0),
        "target": int(_text(node, "targetvolume", "0") or 0),
        "muted": _text(node, "muteenabled", "false").lower() == "true",
    }


def parse_presets(node: ET.Element) -> list[dict[str, Any]]:
    """Parse a <presets> element into a list of preset dicts."""
    presets: list[dict[str, Any]] = []
    for preset in node.findall("preset"):
        content_item = preset.find("ContentItem")
        if content_item is None:
            continue
        presets.append({
            "id": preset.get("id", ""),
            "name": _text(content_item, "itemName"),
            "source": content_item.get("source", ""),
            "type": content_item.get("type", ""),
            "location": content_item.get("location", ""),
            "source_account": content_item.get("sourceAccount", ""),
            "is_presetable": content_item.get("isPresetable", "false").lower() == "true",
            "container_art": _text(content_item, "containerArt"),
        })
    return presets


def parse_sources(node: ET.Element) -> list[dict[str, Any]]:
    """Parse a <sources> element into a list of source dicts."""
    sources: list[dict[str, Any]] = []
    for item in node.findall("sourceItem"):
        sources.append({
            "source": item.get("source", ""),
            "source_account": item.get("sourceAccount", ""),
            "status": item.get("status", ""),
            "is_local": item.get("isLocal", "false").lower() == "true",
            "display_name": (item.text or "").strip(),
        })
    return sources


def parse_info(node: ET.Element) -> dict[str, Any]:
    """Parse an <info> element into a dict."""
    firmware = ""
    for component in node.findall("./components/component"):
        if _text(component, "componentCategory") == "SCM":
            firmware = _text(component, "softwareVersion").split(" ")[0]
            break
    network = node.find("networkInfo")
    return {
        "device_id": node.get("deviceID", ""),
        "name": _text(node, "name"),
        "type": _text(node, "type"),
        "firmware": firmware,
        "mac_address": _text(network, "macAddress") if network is not None else "",
        "ip_address": _text(network, "ipAddress") if network is not None else "",
        "country_code": _text(node, "countryCode"),
        "module_type": _text(node, "moduleType"),
    }


class SoundTouchClient:
    """Talks to a Bose SoundTouch speaker over its local XML API."""

    def __init__(
        self,
        host: str,
        api_port: int = DEFAULT_API_PORT,
        ws_port: int = DEFAULT_WS_PORT,
    ) -> None:
        self._host = host
        self._api_port = int(api_port)
        self._ws_port = int(ws_port)
        self._base = f"http://{host}:{self._api_port}"
        self._session: aiohttp.ClientSession | None = None

    @property
    def host(self) -> str:
        return self._host

    @property
    def ws_url(self) -> str:
        return f"ws://{self._host}:{self._ws_port}/"

    async def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    # -- low level -----------------------------------------------------
    async def _get(self, path: str) -> ET.Element:
        session = await self.session()
        async with session.get(f"{self._base}{path}") as resp:
            resp.raise_for_status()
            body = await resp.text()
        return ET.fromstring(body)

    async def _post(self, path: str, body: str) -> str:
        session = await self.session()
        headers = {"Content-Type": "text/xml"}
        async with session.post(f"{self._base}{path}", data=body, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.text()

    # -- reads ---------------------------------------------------------
    async def get_info(self) -> dict[str, Any]:
        return parse_info(await self._get("/info"))

    async def get_now_playing(self) -> dict[str, Any]:
        return parse_now_playing(await self._get("/now_playing"))

    async def get_volume(self) -> dict[str, Any]:
        return parse_volume(await self._get("/volume"))

    async def get_presets(self) -> list[dict[str, Any]]:
        return parse_presets(await self._get("/presets"))

    async def get_sources(self) -> list[dict[str, Any]]:
        return parse_sources(await self._get("/sources"))

    async def test_connection(self) -> bool:
        try:
            await self._get("/info")
            return True
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.debug("SoundTouch connection test failed for %s: %s", self._host, err)
            return False

    # -- commands ------------------------------------------------------
    async def send_key(self, key: str) -> None:
        """Send a remote key as a press followed by a release."""
        await self._post("/key", f'<key state="press" sender="{WS_SENDER}">{key}</key>')
        await self._post("/key", f'<key state="release" sender="{WS_SENDER}">{key}</key>')

    async def set_volume(self, level: int) -> None:
        level = max(0, min(100, int(level)))
        await self._post("/volume", f"<volume>{level}</volume>")

    async def select_source(self, source: str, source_account: str = "") -> None:
        account = f' sourceAccount="{source_account}"' if source_account else ""
        await self._post("/select", f'<ContentItem source="{source}"{account}></ContentItem>')

    async def select_content_item(
        self,
        source: str,
        item_type: str = "",
        location: str = "",
        source_account: str = "",
        item_name: str = "",
    ) -> None:
        attrs = f'source="{source}"'
        if item_type:
            attrs += f' type="{item_type}"'
        if location:
            attrs += f' location="{location}"'
        if source_account:
            attrs += f' sourceAccount="{source_account}"'
        inner = f"<itemName>{item_name}</itemName>" if item_name else ""
        await self._post("/select", f"<ContentItem {attrs}>{inner}</ContentItem>")

    # -- websocket -----------------------------------------------------
    async def ws_connect(self) -> aiohttp.ClientWebSocketResponse:
        session = await self.session()
        return await session.ws_connect(
            self.ws_url,
            protocols=(WS_SUBPROTOCOL,),
            heartbeat=30,
        )
