import logging
import threading
import time
from typing import Callable
from .api_client import XiaomiIoTClient
from .database import Database

logger = logging.getLogger(__name__)


class Collector:
    def __init__(self, client: XiaomiIoTClient, db: Database,
                 devices_config: list, interval: int = 300, on_data: Callable = None):
        self.client = client
        self.db = db
        self.devices = devices_config
        self.interval = interval
        self.on_data = on_data
        self._running = False
        self._thread = None
        self._last_values = {}

    def collect_once(self):
        results = {}
        for device in self.devices:
            name, did = device["name"], device["did"]
            for prop_name, prop_id in device.get("properties", {}).items():
                try:
                    parts = prop_id.replace("prop.", "").split(".")
                    if len(parts) != 2:
                        continue
                    value = self.client.get_prop(did, int(parts[0]), int(parts[1]))
                    if value is not None:
                        value = float(value)
                        unit = {"temperature": "°C", "humidity": "%", "pm25": "μg/m³"}.get(prop_name, "")
                        self.db.insert_sensor_data(name, did, prop_name, value, unit)
                        self._last_values[f"{name}.{prop_name}"] = value
                        results[f"{name}.{prop_name}"] = value
                        if self.on_data:
                            self.on_data(name, prop_name, value)
                except Exception as e:
                    logger.error("采集异常: %s.%s - %s", name, prop_name, e)
        return results

    def get_latest_values(self):
        return dict(self._last_values)

    def _run_loop(self):
        logger.info("采集器启动，间隔 %d 秒", self.interval)
        while self._running:
            try:
                self.collect_once()
            except Exception as e:
                logger.error("采集异常: %s", e)
            for _ in range(self.interval):
                if not self._running:
                    break
                time.sleep(1)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
