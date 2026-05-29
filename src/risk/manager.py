"""风控管理（复用 A 股版本）"""
import numpy as np
from config import RISK_MAX_DRAWDOWN, RISK_KELLY_FRACTION


class RiskManager:
    def __init__(self, initial_cash: float = 100000):
        self.initial_cash = initial_cash
        self.peak_value = initial_cash

    def check_drawdown(self, current_value: float) -> dict:
        """检查当前回撤"""
        self.peak_value = max(self.peak_value, current_value)
        dd_pct = (current_value - self.peak_value) / self.peak_value if self.peak_value > 0 else 0

        if dd_pct < RISK_MAX_DRAWDOWN:
            level = "critical"
            message = f"回撤 {dd_pct:.1%} 超过阈值 {RISK_MAX_DRAWDOWN:.0%}，暂停交易"
        elif dd_pct < RISK_MAX_DRAWDOWN * 0.7:
            level = "warning"
            message = f"回撤 {dd_pct:.1%} 接近阈值，减仓至 50%"
        else:
            level = "normal"
            message = "正常交易"

        return {
            "dd_pct": round(dd_pct, 4),
            "peak_value": round(self.peak_value, 2),
            "level": level,
            "message": message,
        }

    def kelly_sizing(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Kelly 公式计算最优仓位"""
        if avg_loss == 0:
            return RISK_KELLY_FRACTION
        f = (win_rate * avg_win - (1 - win_rate) * abs(avg_loss)) / abs(avg_loss)
        return max(0, min(f * RISK_KELLY_FRACTION, 0.5))
