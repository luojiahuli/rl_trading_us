"""市场状态分类（复用 A 股版本）"""
import numpy as np
import pandas as pd


class MarketRegimeClassifier:
    def __init__(self):
        self.regime = 0  # 0=未知, 1=牛市, 2=熊市, 3=震荡

    def fit(self, df: pd.DataFrame):
        """根据价格数据分类市场状态"""
        close = df["close"].values
        if len(close) < 60:
            self.regime = 3
            return self

        ret_20d = close[-1] / close[-20] - 1
        ret_60d = close[-1] / close[-60] - 1 if len(close) >= 60 else ret_20d
        volatility = np.std(np.diff(close) / close[:-1]) * np.sqrt(252)

        if ret_60d > 0.1 and volatility < 0.25:
            self.regime = 1  # 牛市
        elif ret_60d < -0.1:
            self.regime = 2  # 熊市
        else:
            self.regime = 3  # 震荡
        return self

    def predict(self, df: pd.DataFrame) -> int:
        return self.regime

    @staticmethod
    def get_regime_name(regime: int) -> str:
        return {1: "牛市", 2: "熊市", 3: "震荡市"}.get(regime, "未知")
