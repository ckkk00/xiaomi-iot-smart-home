import json
import logging
from .api_client import XiaomiIoTClient
from .database import Database

logger = logging.getLogger(__name__)


class Controller:
    def __init__(self, client: XiaomiIoTClient, db: Database, devices_config: list):
        self.client = client
        self.db = db
        self.devices = {d["name"]: d for d in devices_config}

    def execute(self, rule_name, device_name, action, params=None):
        if device_name == "alert":
            logger.warning("[%s] 告警: %s", rule_name, params.get("message", ""))
            self.db.insert_action_log(rule_name, "alert", action, json.dumps(params or {}), True)
            return True

        device = self.devices.get(device_name)
        if not device:
            self.db.insert_action_log(rule_name, device_name, action, "", False, "设备不存在")
            return False

        action_def = device.get("actions", {}).get(action)
        if not action_def:
            self.db.insert_action_log(rule_name, device_name, action, "", False, "动作未定义")
            return False

        params = params or {}
        success = True
        for cmd in action_def:
            value = cmd.get("value")
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                value = params.get(value[1:-1], value)
            if isinstance(value, str):
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
            if cmd.get("aiid") is not None:
                result = self.client.call_action(device["did"], cmd["siid"], cmd["aiid"], [value] if value is not None else [])
            else:
                result = self.client.set_prop(device["did"], cmd["siid"], cmd["piid"], value)
            if not result:
                success = False

        self.db.insert_action_log(rule_name, device_name, action, json.dumps(params), success)
        return success
