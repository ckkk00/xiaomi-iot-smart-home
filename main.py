"""
智能家居环境监测与控制系统 - 入口文件
"""

import logging
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.api_client import XiaomiIoTClient
from src.collector import Collector
from src.controller import Controller
from src.database import Database
from src.dashboard import create_app
from src.rule_engine import RuleEngine


def load_config(path: str) -> dict:
    config_path = ROOT / path
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        print(f"   请先复制模板: cp {path.replace('.yaml', '.example.yaml')} {path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(config: dict):
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)
    log_file = log_config.get("file")
    handlers = [logging.StreamHandler()]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def main():
    print("=" * 50)
    print("  🏠 小米 IoT 智能家居环境监测系统")
    print("=" * 50)

    settings = load_config("config/settings.yaml")
    devices_config = load_config("config/devices.yaml")
    rules_config = load_config("config/rules.yaml")
    setup_logging(settings)
    logger = logging.getLogger(__name__)
    logger.info("配置加载完成")

    xiaomi_cfg = settings.get("xiaomi", {})
    token = xiaomi_cfg.get("token", "")
    if not token or token == "YOUR_MIOT_TOKEN":
        logger.error("❌ 请先在 config/settings.yaml 中配置小米 IoT Token")
        logger.info("   获取方式: https://iot.mi.com")
        sys.exit(1)

    client = XiaomiIoTClient(
        token=token,
        base_url=xiaomi_cfg.get("base_url", "https://api.home.mi.com"),
    )

    db_path = settings.get("database", {}).get("path", "data/smart_home.db")
    db = Database(db_path)

    rules = rules_config.get("rules", [])
    rule_engine = RuleEngine(rules)

    controller_devices = devices_config.get("controllers", [])
    controller = Controller(client, db, controller_devices)

    sensor_devices = devices_config.get("sensors", [])
    collector_interval = settings.get("collector", {}).get("interval", 300)

    def on_sensor_data(device_name: str, prop: str, value: float):
        rule_engine.update_sensor_data(device_name, prop, value)
        if hasattr(app, "emit_sensor_update"):
            app.emit_sensor_update(device_name, prop, value)
        actions = rule_engine.evaluate()
        for action in actions:
            success = controller.execute(
                rule_name=action["rule_name"],
                device_name=action["device"],
                action=action["action"],
                params=action["params"],
            )
            if action["device"] == "alert" and hasattr(app, "emit_alert"):
                msg = action["params"].get("message", "规则触发")
                level = action["params"].get("level", "info")
                app.emit_alert(action["rule_name"], msg, level)

    collector = Collector(
        client=client, db=db, devices_config=sensor_devices,
        interval=collector_interval, on_data=on_sensor_data,
    )

    dash_cfg = settings.get("dashboard", {})
    app, socketio = create_app(db, collector, rule_engine)

    logger.info("🚀 启动采集器...")
    collector.start()

    host = dash_cfg.get("host", "0.0.0.0")
    port = dash_cfg.get("port", 5000)
    debug = dash_cfg.get("debug", False)

    logger.info("🌐 仪表板地址: http://localhost:%d", port)
    print(f"\n  📊 仪表板: http://localhost:{port}")
    print(f"  🔄 采集间隔: {collector_interval} 秒")
    print(f"  📋 规则数量: {len(rules)} 条")
    print(f"  📡 传感器: {len(sensor_devices)} 个")
    print(f"  🎮 控制器: {len(controller_devices)} 个")
    print("\n  按 Ctrl+C 停止\n")

    try:
        socketio.run(app, host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("正在停止...")
        collector.stop()
        logger.info("👋 系统已停止")


if __name__ == "__main__":
    main()
