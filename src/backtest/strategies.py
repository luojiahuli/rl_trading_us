"""策略实现库（复用 A 股版本）"""
import numpy as np
import pandas as pd


class Strategy:
    name = "base"
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError


class TrendFollowingStrategy(Strategy):
    """趋势跟踪：均线金叉死叉"""
    name = "trend_following"
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        signals = np.zeros(len(df))
        for i in range(1, len(df)):
            m5 = df.get("ma5", pd.Series([np.nan] * len(df)))
            m20 = df.get("ma20", pd.Series([np.nan] * len(df)))
            if pd.notna(m5.iloc[i]) and pd.notna(m20.iloc[i]):
                if m5.iloc[i-1] <= m20.iloc[i-1] and m5.iloc[i] > m20.iloc[i]:
                    signals[i] = 1
                elif m5.iloc[i-1] >= m20.iloc[i-1] and m5.iloc[i] < m20.iloc[i]:
                    signals[i] = -1
        return signals


class MeanReversionStrategy(Strategy):
    """均值回归：RSI 超买超卖"""
    name = "mean_reversion"
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        signals = np.zeros(len(df))
        for i in range(len(df)):
            rsi = df.get("rsi_14", pd.Series([50] * len(df))).iloc[i]
            if pd.isna(rsi):
                continue
            if rsi < 30:
                signals[i] = 1
            elif rsi > 70:
                signals[i] = -1
        return signals


class BreakoutStrategy(Strategy):
    """突破策略：Bollinger 突破"""
    name = "breakout"
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        signals = np.zeros(len(df))
        for i in range(1, len(df)):
            close = df["close"].iloc[i]
            upper = df.get("boll_upper", pd.Series([np.nan] * len(df))).iloc[i]
            lower = df.get("boll_lower", pd.Series([np.nan] * len(df))).iloc[i]
            vol_ratio = df.get("volume_ratio", pd.Series([1] * len(df))).iloc[i]
            if pd.isna(upper) or pd.isna(lower):
                continue
            if close > upper and vol_ratio > 1.5:
                signals[i] = 1
            elif close < lower and vol_ratio > 1.5:
                signals[i] = -1
        return signals


class MomentumStrategy(Strategy):
    """动量策略"""
    name = "momentum"
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        signals = np.zeros(len(df))
        for i in range(5, len(df)):
            ret_5d = df["close"].iloc[i] / df["close"].iloc[i-5] - 1
            vol_ratio = df.get("volume_ratio", pd.Series([1] * len(df))).iloc[i]
            if ret_5d > 0.05 and vol_ratio > 1.2:
                signals[i] = 1
            elif ret_5d < -0.05 and vol_ratio > 1.2:
                signals[i] = -1
        return signals


def get_all_strategies() -> list:
    return [
        TrendFollowingStrategy(),
        MeanReversionStrategy(),
        BreakoutStrategy(),
        MomentumStrategy(),
    ]
