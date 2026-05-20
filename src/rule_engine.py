import logging
import operator
import time

logger = logging.getLogger(__name__)

OPERATORS = {">": operator.gt, "<": operator.lt, ">=": operator.ge,
             "<=": operator.le, "==": operator.eq, "!=": operator.ne}


class Rule:
    def __init__(self, config: dict):
        self.name = config["name"]
        self.description = config.get("description", "")
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", 10)
        self.cooldown = config.get("cooldown", 0)
        self.condition = config["condition"]
        self.actions = config.get("actions", [])
        self._last_triggered = 0

    def is_in_cooldown(self):
        return self.cooldown > 0 and (time.time() - self._last_triggered) < self.cooldown

    def mark_triggered(self):
        self._last_triggered = time.time()


class RuleEngine:
    def __init__(self, rules_config: list):
        self.rules = []
        self._sensor_data = {}
        for cfg in rules_config:
            rule = Rule(cfg)
            if rule.enabled:
                self.rules.append(rule)
                logger.info("加载规则: [%s] %s", rule.name, rule.condition)
        self.rules.sort(key=lambda r: r.priority)
        logger.info("共加载 %d 条规则", len(self.rules))

    def update_sensor_data(self, device_name, prop, value):
        self._sensor_data[f"sensors.{device_name}.{prop}"] = value

    def _eval_condition(self, condition):
        try:
            if " and " in condition:
                return all(self._eval_condition(p.strip()) for p in condition.split(" and "))
            if " or " in condition:
                return any(self._eval_condition(p.strip()) for p in condition.split(" or "))

            tokens = condition.strip().split()
            if len(tokens) != 3:
                return False

            sensor_ref, op_str, value_str = tokens
            sensor_val = self._sensor_data.get(sensor_ref)
            if sensor_val is None:
                return False

            op_func = OPERATORS.get(op_str)
            if not op_func:
                return False

            result = op_func(float(sensor_val), float(value_str))
            if result:
                logger.info("条件命中: %s (当前值=%s)", condition, sensor_val)
            return result
        except Exception as e:
            logger.error("条件求值异常: %s - %s", condition, e)
            return False

    def evaluate(self):
        triggered = []
        for rule in self.rules:
            if rule.is_in_cooldown():
                continue
            if self._eval_condition(rule.condition):
                rule.mark_triggered()
                logger.info("规则触发: %s", rule.name)
                for a in rule.actions:
                    triggered.append({"rule_name": rule.name, "device": a["device"],
                                      "action": a["action"], "params": a.get("params", {})})
        return triggered

    def get_rules_status(self):
        return [{"name": r.name, "description": r.description, "enabled": r.enabled,
                 "priority": r.priority, "cooldown": r.cooldown, "condition": r.condition,
                 "last_triggered": r._last_triggered, "in_cooldown": r.is_in_cooldown()} for r in self.rules]
