import os
import json
from typing import Dict, Any, List, Optional
import requests
from PySide6.QtCore import QThread, Signal


class RemoteConfigLoaderWorker(QThread):
    config_updated = Signal(dict)

    def __init__(self, remote_url: str, parent=None):
        super().__init__(parent)
        self.remote_url = remote_url

    def run(self):
        try:
            resp = requests.get(self.remote_url, timeout=3.5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "domains" in data:
                    self.config_updated.emit(data)
        except Exception:
            pass


class RemoteConfigManager:
    """
    Dual-layer Remote Configuration Manager.
    Loads local baseline config first, then attempts asynchronous remote update.
    """
    _instance: Optional['RemoteConfigManager'] = None

    def __init__(self):
        self.config_data = {}
        self._load_local_config()

    @classmethod
    def get_instance(cls) -> 'RemoteConfigManager':
        if cls._instance is None:
            cls._instance = RemoteConfigManager()
        return cls._instance

    def _load_local_config(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_path = os.path.join(base_dir, "config", "remote_config.json")
        if not os.path.exists(local_path):
            local_path = os.path.join(base_dir, "resources", "remote_config.json")
        if os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    self.config_data = json.load(f)
            except Exception:
                self.config_data = {}

    def fetch_remote(self, url: str):
        worker = RemoteConfigLoaderWorker(url)
        worker.config_updated.connect(self._on_remote_updated)
        worker.start()
        # Keep reference to worker
        self._worker = worker

    def _on_remote_updated(self, new_data: dict):
        self.config_data.update(new_data)

    def get_domain(self, name: str, default: str = "") -> str:
        return self.config_data.get("domains", {}).get(name, default)

    def get_iptv_channels(self) -> List[Dict[str, Any]]:
        return self.config_data.get("iptv_channels", [])

    def get_oscar_vod_config(self) -> Dict[str, Any]:
        """
        Returns the isolated Oscar TV / Media App VOD configuration
        including base URL, authentication tokens, endpoints, and headers.
        """
        defaults = {
            "base_url": "https://api.oscar-tv.net/api/v1",
            "token": "bearer_oscar_vod_token_live_2026",
            "user_agent": "OscarTV-VOD/3.4.0 (Linux; Android 12; Build/SQ1D.220205.004)",
            "app_id": "com.oscartv.app",
            "endpoints": {
                "movie_servers": "/vod/movie/{id}/servers",
                "series_servers": "/vod/series/{id}/season/{season}/episode/{episode}/servers",
                "search": "/vod/search?q={query}"
            },
            "timeout_seconds": 4.0
        }
        loaded = self.config_data.get("oscar_vod", {})
        merged = dict(defaults)
        merged.update(loaded)
        return merged
