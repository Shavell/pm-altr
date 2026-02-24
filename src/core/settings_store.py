"""Persistent settings storage — saved to ~/.pm-altr/settings.json."""
from __future__ import annotations
import json
from pathlib import Path

_SETTINGS_PATH = Path.home() / ".pm-altr" / "settings.json"

_DEFAULTS: dict = {
    "proxy_enabled": False,
    "proxy_use_system": False,
    "proxy_host": "",
    "proxy_port": "",
    "proxy_username": "",
    "proxy_password": "",
    "proxy_no_proxy": "",
    "ssl_verify": True,
    "follow_redirects": True,
}


def load_settings() -> dict:
    if _SETTINGS_PATH.exists():
        try:
            data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
            return {**_DEFAULTS, **data}
        except Exception:
            pass
    return dict(_DEFAULTS)


def save_settings(settings: dict):
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def proxy_url(settings: dict) -> str:
    """Build a proxy URL like http://user:pass@host:port from settings."""
    host = settings.get("proxy_host", "").strip()
    port = settings.get("proxy_port", "").strip()
    user = settings.get("proxy_username", "").strip()
    password = settings.get("proxy_password", "").strip()
    if not host:
        return ""
    auth = f"{user}:{password}@" if user else ""
    port_part = f":{port}" if port else ""
    return f"http://{auth}{host}{port_part}"
