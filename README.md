# Bose SoundTouch Integration for Unfolded Circle Remote 2/3

Control your **Bose SoundTouch** speakers directly from your Unfolded Circle Remote 2 or Remote 3 over the local network. Power, volume, mute, transport, source switching, presets, and live now-playing metadata with album art - no cloud, no app required.

![Bose SoundTouch](https://img.shields.io/badge/Bose-SoundTouch-blue)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-soundtouch?style=flat-square)](https://github.com/mase1981/uc-intg-soundtouch/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-soundtouch?style=flat-square)](https://github.com/mase1981/uc-intg-soundtouch/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://unfolded.community/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-soundtouch/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)

## Features

The integration talks to your speaker over the Bose SoundTouch local XML API and gets real-time updates through the speaker's own WebSocket notification channel, so state on the Remote stays in sync the moment anything changes (even from the Bose app or the speaker's buttons):

- **🎵 Full media player** - power on/off, volume, mute, play/pause, stop, next/previous, and live **now-playing** metadata (track, artist, album, and **album art**).
- **🔀 Source switching** - select **AUX** or **Bluetooth** directly from the media player.
- **⭐ 6 presets** - a Select entity to recall any of the speaker's 6 stored presets by name.
- **🎛️ Remote entity** - every SoundTouch key (transport, presets, sources, shuffle/repeat, thumbs) exposed as simple commands with discrete **Power On / Power Off** for use in Activities, plus a ready-made button page.
- **📊 Sensors** - a **Source** sensor and a **Now Playing** sensor for use on any page or in automations.
- **⚡ Real-time updates** via SoundTouch's WebSocket, with automatic polling fallback for robustness.
- **Multi-speaker** - add each SoundTouch speaker as its own device.

---
## ❤️ Support Development ❤️

If you find this integration useful, consider supporting development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️
---

## Requirements

- A Bose SoundTouch speaker (SoundTouch 10/20/30, 300, Wave SoundTouch, Portable, etc.) on the same network as your Remote.
- The speaker's IP address (a static/reserved DHCP lease is recommended so it doesn't change).
- Unfolded Circle Remote 2 / 3 with firmware supporting custom integrations.

## Installation

### Option 1: Remote Web Interface (Recommended)

1. Download the latest `uc-intg-soundtouch-<version>.tar.gz` from the [**Releases**](https://github.com/mase1981/uc-intg-soundtouch/releases) page.
2. Open your Remote's web interface (`http://your-remote-ip`).
3. Go to **Settings -> Integrations -> Add Integration -> Install Custom** and upload the `.tar.gz`.

### Option 2: Docker (Advanced Users)

The integration is available as a pre-built Docker image from GitHub Container Registry:

**Image**: `ghcr.io/mase1981/uc-intg-soundtouch:latest`

**Docker Compose:**
```yaml
services:
  uc-intg-soundtouch:
    image: ghcr.io/mase1981/uc-intg-soundtouch:latest
    container_name: uc-intg-soundtouch
    network_mode: host
    volumes:
      - ./config:/config
    environment:
      - UC_CONFIG_HOME=/config
      - UC_INTEGRATION_HTTP_PORT=9090
      - UC_INTEGRATION_INTERFACE=0.0.0.0
      - PYTHONPATH=/app
    restart: unless-stopped
```

**Docker Run:**
```bash
docker run -d --name uc-intg-soundtouch --restart unless-stopped --network host -v $(pwd)/config:/config -e UC_CONFIG_HOME=/config -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 -e PYTHONPATH=/app ghcr.io/mase1981/uc-intg-soundtouch:latest
```

## Configuration

Setup is a **single screen**: enter your SoundTouch speaker's **IP address**. That's it - the speaker's name, sources, and presets are discovered automatically.

For each speaker, the integration creates:

| Entity | Purpose |
|--------|---------|
| **Media player** (`<name>`) | Power, volume, mute, transport, source select, and now-playing with album art. |
| **Remote** (`<name> Remote`) | All SoundTouch keys as simple commands (transport, presets, sources, power on/off) for Activities. |
| **Select** (`<name> Preset`) | Recall any of the 6 stored presets by name. |
| **Sensors** (`<name> Source`, `<name> Now Playing`) | Current source and now-playing text. |

## Using the Integration

1. Add the **media player** to a page or Activity for full control with now-playing and album art.
2. Use the **Preset** select to recall a stored station/playlist by name.
3. Add the **Remote** entity to an Activity to sequence commands (e.g. Power On -> select Bluetooth), using the discrete **POWER_ON** / **POWER_OFF** commands.
4. Drop the **Source** and **Now Playing** sensors onto any page to see status at a glance.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Cannot reach a Bose SoundTouch speaker" | Verify the IP; open `http://<speaker-ip>:8090/info` in a browser to confirm the speaker's API is reachable. |
| Speaker not responding after a router reboot | The speaker's IP may have changed - reserve a static DHCP lease and re-run setup if needed. |
| State not updating | The integration uses the speaker's WebSocket with a polling fallback; give it a few seconds or confirm the speaker is on the same subnet as the Remote. |
| Source switch does nothing | Only **AUX** and **Bluetooth** are directly selectable; streaming services are recalled via **presets**. |
| Power On/Off seems inverted | SoundTouch's power is a toggle; the integration reads the speaker's real state, so use the discrete POWER_ON / POWER_OFF commands in Activities. |

## Credits

- **Developer**: Meir Miyara
- **Bose SoundTouch**: local XML API on the speaker (protocol referenced from the community `libsoundtouch` / Home Assistant SoundTouch integration).
- **Unfolded Circle**: Remote 2/3 integration framework ([ucapi](https://github.com/unfoldedcircle/integration-python-library) / [ucapi-framework](https://github.com/JackJPowell/ucapi-framework)).

## License

Mozilla Public License 2.0 (MPL-2.0) - see the LICENSE file.

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-soundtouch/issues)
- **UC Community Forum**: [General discussion and support](https://unfolded.community/)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)

---

**Made with ❤️ for the Unfolded Circle Community**

**Thank You**: Meir Miyara
