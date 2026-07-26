"""Setup flow for the Bose SoundTouch integration: enter IP, auto-discover."""

import logging
import re
from typing import Any

from ucapi import RequestUserInput
from ucapi_framework import BaseSetupFlow

from uc_intg_soundtouch.client import SoundTouchClient
from uc_intg_soundtouch.config import SoundTouchConfig
from uc_intg_soundtouch.const import DEFAULT_API_PORT, DEFAULT_WS_PORT

_LOG = logging.getLogger(__name__)


class SoundTouchSetupFlow(BaseSetupFlow[SoundTouchConfig]):
    """Single screen: SoundTouch speaker IP. Name and capabilities discovered."""

    def get_manual_entry_form(self) -> RequestUserInput:
        return RequestUserInput(
            {"en": "Bose SoundTouch Setup"},
            [
                {
                    "id": "info",
                    "label": {"en": "Bose SoundTouch speaker"},
                    "field": {"label": {"value": {"en": "Enter the IP address of your Bose SoundTouch speaker. Its name, sources, and presets are discovered automatically."}}},
                },
                {"id": "host", "label": {"en": "IP address"}, "field": {"text": {"value": ""}}},
            ],
        )

    async def query_device(self, input_values: dict[str, Any]) -> SoundTouchConfig | RequestUserInput:
        host = input_values.get("host", "").strip()
        if not host:
            raise ValueError("IP address is required")

        client = SoundTouchClient(host, DEFAULT_API_PORT, DEFAULT_WS_PORT)
        try:
            if not await client.test_connection():
                raise ValueError(f"Cannot reach a Bose SoundTouch speaker at {host}")
            info = await client.get_info()
        finally:
            await client.close()

        device_id = info.get("device_id") or info.get("mac_address") or host
        name = info.get("name", "").strip() or f"SoundTouch ({host})"
        identifier = f"soundtouch_{re.sub(r'[^A-Za-z0-9]', '_', device_id)}"

        _LOG.info("SoundTouch %s — %s (%s), firmware %s",
                  host, name, info.get("type", "?"), info.get("firmware", "?"))
        return SoundTouchConfig(
            identifier=identifier,
            name=name,
            host=host,
            api_port=DEFAULT_API_PORT,
            ws_port=DEFAULT_WS_PORT,
        )
