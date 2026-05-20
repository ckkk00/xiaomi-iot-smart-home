# Xiaomi IoT Smart Home - 环境监测与控制系统

基于小米 IoT 开发者平台的智能家居环境监测与自动联动控制系统。

## 系统架构

感知层(Collector) → 推理层(RuleEngine) → 执行层(Controller) → 储存层(Database) → 展示层(Dashboard)

| 层级 | 模块 | 职责 |
|------|------|------|
| 感知层 | src/collector.py | 每5分钟轮询传感器，采集温度/湿度/PM2.5 |
| 推理层 | src/rule_engine.py | YAML声明式规则引擎，条件求值→命中判断 |
| 执行层 | src/controller.py | 规则命中后调用小米IoT API控制设备 |
| 储存层 | src/database.py | SQLite持久化存储环境数据与执行日志 |
| 展示层 | src/dashboard.py | Flask + ECharts 实时仪表板 |

## 快速开始

```bash
# 1. 安装依赖
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. 配置
cp config/settings.example.yaml config/settings.yaml
cp config/devices.example.yaml config/devices.yaml
cp config/rules.example.yaml config/rules.yaml
# 编辑 settings.yaml 填入小米 IoT Token

# 3. 运行
python main.py
