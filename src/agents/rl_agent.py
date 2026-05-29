"""RL 交易决策 Agent（美股版，复用 A 股逻辑）"""
from ..agents.base import AgentContext, BaseAgent
from config import RL_BUY_POSITION_PCT


def infer_strategy(rsi, price_pos, volume_ratio, pct_chg, ts_hits):
    if any(s["type"] in ("valley", "up_trend_start") for s in ts_hits):
        return "趋势跟踪"
    if any(s["type"] in ("lower_breakout", "upper_breakout") for s in ts_hits):
        return "突破策略"
    if rsi < 35 or rsi > 70:
        return "均值回归"
    if volume_ratio > 1.5:
        return "动量策略"
    return "趋势跟踪"


class RLTradingAgent(BaseAgent):
    name = "rl_trading"
    description = "强化学习交易决策 - 美股版"

    def execute(self, context: AgentContext) -> AgentContext:
        signals = []
        for code in context.stock_pool:
            ind = context.indicators.get(code, {})
            if not ind:
                continue
            rsi = ind.get("rsi_14", 50)
            price_pos = ind.get("price_position", 0.5)
            volume_ratio = ind.get("volume_ratio", 1)
            pct_chg = ind.get("pct_chg", 0)
            ts_hits = [s for s in context.ts_signals if s.get("stock") == code]

            buy_score = 0
            if rsi < 35 and price_pos < 0.3:
                buy_score += 2
            if volume_ratio > 1.5 and pct_chg > 0:
                buy_score += 2
            if any(s["type"] in ("valley", "up_trend_start") for s in ts_hits):
                buy_score += 2
            if any(s["type"] == "lower_breakout" for s in ts_hits):
                buy_score += 1

            sell_score = 0
            if rsi > 70 and price_pos > 0.8:
                sell_score += 2
            if volume_ratio > 2 and pct_chg < 0:
                sell_score += 2
            if any(s["type"] in ("peak", "down_trend_start") for s in ts_hits):
                sell_score += 2

            if buy_score >= 2 and buy_score > sell_score:
                action = "buy"
                confidence = min(1.0, buy_score / 5)
            elif sell_score >= 2 and sell_score > buy_score:
                action = "sell"
                confidence = min(1.0, sell_score / 5)
            else:
                continue

            strategy = infer_strategy(rsi, price_pos, volume_ratio, pct_chg, ts_hits)
            signals.append({
                "stock": code,
                "action": action,
                "strategy": strategy,
                "confidence": round(confidence, 3),
                "price": ind.get("close", 0),
                "position_pct": RL_BUY_POSITION_PCT if action == "buy" else 1.0,
                "reason": f"RSI={rsi}, 价格位置={price_pos:.2f}, 量比={volume_ratio:.2f}",
            })

        signals.sort(key=lambda x: x["confidence"], reverse=True)
        context.rl_signals = signals
        context.warnings.append(f"美股: 生成 {len(signals)} 个交易信号")
        return context
