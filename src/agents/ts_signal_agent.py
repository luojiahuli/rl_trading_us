"""时间序列信号 Agent（复用 A 股逻辑）"""
import numpy as np
from ..agents.base import AgentContext, BaseAgent


def detect_ts_patterns(df, code):
    """检测时间序列模式：谷底、峰值、趋势起点等"""
    signals = []
    close = df["close"].values
    if len(close) < 20:
        return signals

    rsi = df.get("rsi_14", pd.Series([50] * len(close))).values if hasattr(df, 'get') else np.full(len(close), 50)
    volume = df["volume"].values
    volume_ma5 = df.get("volume_ma5", pd.Series(volume)).values

    # 谷底检测：价格连续下跌后反弹
    for i in range(10, len(close)):
        if all(close[i - j] < close[i - j - 1] for j in range(3)) and close[i] > close[i - 1]:
            signals.append({"stock": code, "type": "valley", "index": i, "price": close[i], "confidence": 0.7})
            break

    # 峰值检测
    for i in range(10, len(close)):
        if all(close[i - j] > close[i - j - 1] for j in range(3)) and close[i] < close[i - 1]:
            signals.append({"stock": code, "type": "peak", "index": i, "price": close[i], "confidence": 0.7})
            break

    # 上升趋势起点
    if rsi[-1] > rsi[-5] and close[-1] > close[-5]:
        signals.append({"stock": code, "type": "up_trend_start", "index": len(close) - 1,
                        "price": close[-1], "confidence": 0.6})

    # 下降趋势起点
    if rsi[-1] < rsi[-5] and close[-1] < close[-5]:
        signals.append({"stock": code, "type": "down_trend_start", "index": len(close) - 1,
                        "price": close[-1], "confidence": 0.6})

    # 放量突破
    if len(close) > 5 and volume[-1] > volume_ma5[-1] * 1.5 and close[-1] > close[-2]:
        signals.append({"stock": code, "type": "lower_breakout", "index": len(close) - 1,
                        "price": close[-1], "confidence": 0.5})

    return signals


import pandas as pd


class TimeSeriesSignalAgent(BaseAgent):
    name = "ts_signal"
    description = "检测时间序列模式信号"

    def execute(self, context: AgentContext) -> AgentContext:
        all_signals = []
        for code, df in context.market_data.items():
            if len(df) < 20:
                continue
            try:
                sigs = detect_ts_patterns(df, code)
                all_signals.extend(sigs)
            except Exception:
                continue
        context.ts_signals = all_signals
        context.warnings.append(f"检测到 {len(all_signals)} 个时间序列信号")
        return context
