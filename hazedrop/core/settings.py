from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


_CONFIG_PATH = os.path.expanduser("~/.config/hazedrop/settings.json")


@dataclass
class Settings:
    download_dir: str = field(default_factory=lambda: os.path.expanduser("~/Downloads"))
    default_once: bool = True
    default_expire: str = ""
    tor_bridges: list = field(default_factory=list)
    use_bridges: bool = False
    history_enabled: bool = True
    history_ttl_days: int = 7
    minimize_to_tray: bool = True
    max_downloads: int = 1
    language: str = "en"
    # Base64 QByteArray from QWidget.saveGeometry(), so the window reopens
    # where the user left it instead of always at 820x600 top-left.
    window_geometry: str = ""


def load_settings() -> Settings:
    try:
        os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            s = Settings()
            s.download_dir = data.get("download_dir", s.download_dir)
            s.default_once = data.get("default_once", s.default_once)
            s.default_expire = data.get("default_expire", s.default_expire)
            s.tor_bridges = data.get("tor_bridges", s.tor_bridges)
            s.use_bridges = data.get("use_bridges", s.use_bridges)
            s.history_enabled = data.get("history_enabled", s.history_enabled)
            s.history_ttl_days = data.get("history_ttl_days", s.history_ttl_days)
            s.minimize_to_tray = data.get("minimize_to_tray", s.minimize_to_tray)
            s.max_downloads = data.get("max_downloads", s.max_downloads)
            s.language = data.get("language", s.language)
            s.window_geometry = data.get("window_geometry", s.window_geometry)
            return s
    except Exception:
        pass
    return Settings()


def save_settings(s: Settings) -> None:
    try:
        os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
        data = {
            "download_dir": s.download_dir,
            "default_once": s.default_once,
            "default_expire": s.default_expire,
            "tor_bridges": s.tor_bridges,
            "use_bridges": s.use_bridges,
            "history_enabled": s.history_enabled,
            "history_ttl_days": s.history_ttl_days,
            "minimize_to_tray": s.minimize_to_tray,
            "max_downloads": s.max_downloads,
            "language": s.language,
            "window_geometry": s.window_geometry,
        }
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
