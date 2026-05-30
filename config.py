"""美股量化交易系统配置"""
import os

# 飞书配置
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_CHAT_ID = os.getenv("FEISHU_CHAT_ID", "")

# 数据范围
START_DATE = "2024-01-01"
END_DATE = None  # None 表示到最新交易日

# 美股过滤规则：排除低价股（penny stocks < $5）
MIN_STOCK_PRICE = 5.0

# 资金与仓位管理
INITIAL_CASH = 1_000_000
RL_TOTAL_TIMESTEPS = 200_000
RL_BUY_POSITION_PCT = 0.2
RL_ADD_POSITION_PCT = 0.1
RL_MAX_POSITIONS = 5
RL_STOP_LOSS = -0.08
RL_STOP_LOSS_WARN = -0.05

# 风控参数
RISK_MAX_DRAWDOWN = -0.15
RISK_KELLY_FRACTION = 0.25

# LLM 配置（预留）
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

# 目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
REPORT_DIR = os.path.join(OUTPUT_DIR, "reports")
MODEL_DIR = os.path.join(OUTPUT_DIR, "models")
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")
DB_PATH = os.path.join(OUTPUT_DIR, "trading_us.db")
