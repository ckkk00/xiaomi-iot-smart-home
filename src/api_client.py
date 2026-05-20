"""
小米 IoT API 客户端
封装小米 IoT 开发者平台的 HTTP API 调用
"""

import hashlib
import json
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class XiaomiIoTClient:

    def __init__(self, token: str, base_url: str = "https://api.home.mi.com"):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "XiaomiSmartHome/1.0",
        })

    def _sign(self, payload: dict) -> dict:
        nonce = str(int(time.time() * 1000))
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        sign_str = f"{nonce}{data}{self.token}"
        signature = hashlib.sha256(sign_str.encode()).hexdigest()
        return {"nonce": nonce, "data": data, "signature": signature}

    def _request(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        signed = self._sign(payload)
        signed["token"] = self.token
        try:
            resp = self.session.post(url, json=signed, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                logger.error("API 错误: %s - %s", result.get("code"), result.get("message"))
                return {"error": result.get("message", "Unknown error"), "code": result.get("code")}
            return result.get("result", result)
        except requests.RequestException as e:
            logger.error("请求失败: %s", e)
            return {"error": str(e)}

    def get_prop(self, did: str, siid: int, piid: int) -> Any:
        payload = {"params": [{"did": did, "siid": siid, "piid": piid}]}
        result = self._request("/miotspec/prop/get", payload)
        if "error" in result:
            return None
        values = result.get("value", [])
        if values and len(values) > 0:
            return values[0].get("value")
        return None

    def set_prop(self, did: str, siid: int, piid: int, value: Any) -> bool:
        payload = {"params": [{"did": did, "siid": siid, "piid": piid, "value": value}]}
        result = self._request("/miotspec/prop/set", payload)
        return "error" not in result

    def call_action(self, did: str, siid: int, aiid: int, params: list | None = None) -> bool:
        payload = {"params": {"did": did, "siid": siid, "aiid": aiid, "in": params or []}}
        result = self._request("/miotspec/action", payload)
        return "error" not in result

    def get_device_list(self) -> list:
        result = self._request("/miotspec/device/list", {})
        if "error" in result:
            return []
        return result.get("list", [])

    def get_device_info(self, did: str) -> dict:
        result = self._request("/miotspec/device/info", {"did": did})
        if "error" in result:
            return {}
        return result
