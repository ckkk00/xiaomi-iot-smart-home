import logging
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
from .database import Database

logger = logging.getLogger(__name__)


def create_app(db: Database, collector=None, rule_engine=None):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["SECRET_KEY"] = "xiaomi-smart-home"
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

    @app.route("/")
    def index():
        return render_template("dashboard.html")

    @app.route("/api/sensors")
    def api_sensors():
        if not collector:
            return jsonify([])
        values = collector.get_latest_values()
        result = []
        for key, value in values.items():
            parts = key.split(".", 1)
            result.append({"device": parts[0], "property": parts[1] if len(parts) > 1 else "",
                           "value": value, "unit": {"temperature": "°C", "humidity": "%", "pm25": "μg/m³"}.get(parts[1] if len(parts) > 1 else "", ""),
                           "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify(result)

    @app.route("/api/sensors/<device>/<prop>/history")
    def api_sensor_history(device, prop):
        return jsonify(db.get_sensor_history(device, prop, hours=request.args.get("hours", 24, type=int)))

    @app.route("/api/sensors/<device>/<prop>/stats")
    def api_sensor_stats(device, prop):
        return jsonify(db.get_sensor_stats(device, prop, hours=request.args.get("hours", 24, type=int)))

    @app.route("/api/actions")
    def api_actions():
        return jsonify(db.get_action_logs(limit=request.args.get("limit", 50, type=int)))

    @app.route("/api/rules")
    def api_rules():
        return jsonify(rule_engine.get_rules_status() if rule_engine else [])

    def emit_sensor_update(device_name, prop, value):
        socketio.emit("sensor_update", {"device": device_name, "property": prop, "value": value, "timestamp": time.time()})

    def emit_alert(rule_name, message, level="warning"):
        socketio.emit("alert", {"rule": rule_name, "message": message, "level": level, "timestamp": time.time()})

    app.emit_sensor_update = emit_sensor_update
    app.emit_alert = emit_alert
    return app, socketio
