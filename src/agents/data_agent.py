"""数据获取 Agent — 美股版（yfinance，无后缀）"""
import time
import pandas as pd
from ..agents.base import AgentContext, BaseAgent
from ..data.fetcher import fetch_stock_daily
from ..data.indicators import compute_indicators
from ..data.sector_map import _SECTOR_STOCK_MAP_US
from config import START_DATE, END_DATE, MIN_STOCK_PRICE


class DataFetchAgent(BaseAgent):
    name = "data_fetch"
    description = "获取美股行情数据并计算技术指标"

    def execute(self, context: AgentContext) -> AgentContext:
        stock_pool = []
        market_data = {}
        all_indicators = {}

        for sector in context.hot_sectors:
            stocks = sector.get("stocks", [])[:6]
            for code in stocks:
                if code in stock_pool:
                    continue
                df = fetch_stock_daily(code, START_DATE, END_DATE)
                if df is None or len(df) < 30:
                    context.warnings.append(f"{code}: 数据不足，跳过")
                    continue
                last_close = df["close"].iloc[-1]
                if last_close < MIN_STOCK_PRICE:
                    context.warnings.append(f"{code}: 低于 ${MIN_STOCK_PRICE}，跳过")
                    continue
                stock_pool.append(code)
                market_data[code] = df
                ind_df = compute_indicators(df)
                last = ind_df.iloc[-1]
                all_indicators[code] = {
                    "close": float(last["close"]),
                    "pct_chg": float(last["pct_chg"]) if pd.notna(last["pct_chg"]) else 0.0,
                    "volume_ratio": float(last["volume_ratio"]) if pd.notna(last["volume_ratio"]) else 1.0,
                    "rsi_14": float(last["rsi_14"]) if pd.notna(last["rsi_14"]) else 50.0,
                    "price_position": float(last["price_position"]),
                    "atr": float(last["atr"]) if pd.notna(last["atr"]) else 0.0,
                    "ma5": float(last["ma5"]) if pd.notna(last["ma5"]) else 0.0,
                    "ma10": float(last["ma10"]) if pd.notna(last["ma10"]) else 0.0,
                    "ma20": float(last["ma20"]) if pd.notna(last["ma20"]) else 0.0,
                    "ma50": float(last.get("ma50", last.get("ma60", 0))) if pd.notna(last.get("ma50", last.get("ma60", 0))) else 0.0,
                    "ma60": float(last["ma60"]) if pd.notna(last["ma60"]) else 0.0,
                }
                time.sleep(0.3)

        context.stock_pool = stock_pool
        context.market_data = market_data
        context.indicators = all_indicators
        context.warnings.append(f"美股数据获取完成: {len(stock_pool)} 只股票")
        return context
