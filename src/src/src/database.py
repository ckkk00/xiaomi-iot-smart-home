"""
SQLite 数据存储层
"""

import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:

    def __init__(self, db_path: str = "data/smart_home.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_name TEXT NOT NULL,
                    device_did TEXT NOT NULL,
                    property TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    timestamp REAL NOT NULL,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                );
                CREATE INDEX IF NOT EXISTS idx_sensor_device ON sensor_data(device_name, property);
                CREATE INDEX IF NOT EXISTS idx_sensor_time ON sensor_data(timestamp);

                CREATE TABLE IF NOT EXISTS action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT,
                    device_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    params TEXT,
                    success INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    timestamp REAL NOT NULL,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                );
                CREATE INDEX IF NOT EXISTS idx_action_time ON action_log(timestamp);
                CREATE INDEX IF NOT EXISTS idx_action_rule ON action_log(rule_name);

                CREATE TABLE IF NOT EXISTS rule_trigger_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT NOT NULL,
                    condition TEXT,
                    matched INTEGER NOT NULL DEFAULT 0,
                    timestamp REAL NOT NULL,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                );
            """)
        logger.info("数据库初始化完成: %s", self.db_path)

    def insert_sensor_data(self, device_name: str, device_did: str, prop: str, value: float, unit: str = ""):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO sensor_data (device_name, device_did, property, value, unit, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (device_name, device_did, prop, value, unit, time.time()),
            )

    def insert_action_log(self, rule_name: str, device_name: str, action: str, params: str, success: bool, error: str = ""):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO action_log (rule_name, device_name, action, params, success, error_message, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (rule_name, device_name, action, params, int(success), error, time.time()),
            )

    def insert_rule_trigger(self, rule_name: str, condition: str, matched: bool):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO rule_trigger_log (rule_name, condition, matched, timestamp) VALUES (?, ?, ?, ?)",
                (rule_name, condition, int(matched), time.time()),
            )

    def get_latest_sensor_data(self, device_name: str, prop: str, limit: int = 1) -> list:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sensor_data WHERE device_name=? AND property=? ORDER BY timestamp DESC LIMIT ?",
                (device_name, prop, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_sensor_history(self, device_name: str, prop: str, hours: int = 24, limit: int = 500) -> list:
        since = time.time() - hours * 3600
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT value, timestamp, created_at FROM sensor_data WHERE device_name=? AND property=? AND timestamp>? ORDER BY timestamp ASC LIMIT ?",
                (device_name, prop, since, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_action_logs(self, limit: int = 100) -> list:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM action_log ORDER BY timestamp DESC LIMIT ?", (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_sensor_stats(self, device_name: str, prop: str, hours: int = 24) -> dict:
        since = time.time() - hours * 3600
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT MIN(value) as min_val, MAX(value) as max_val, AVG(value) as avg_val, COUNT(*) as count FROM sensor_data WHERE device_name=? AND property=? AND timestamp>?",
                (device_name, prop, since),
            ).fetchone()
            return dict(row) if row else {}
