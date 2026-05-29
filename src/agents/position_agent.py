"""持仓分析 Agent（港股版）"""
from ..agents.base import AgentContext, BaseAgent
from config import INITIAL_CASH


class PositionAnalysisAgent(BaseAgent):
    name = "position_analysis"
    description = "港股持仓明细分析"

    def execute(self, context: AgentContext) -> AgentContext:
        if not context.trades:
            context.position_analysis = {
                "positions": [],
                "summary": {
                    "initial_cash": INITIAL_CASH,
                    "cash": INITIAL_CASH,
                    "stock_value": 0,
                    "total_assets": INITIAL_CASH,
                    "total_return": 0,
                    "active_positions": 0,
                },
            }
            return context

        positions = []
        cash = float(INITIAL_CASH)
        stock_value = 0
        strategy_map = {}

        for t in context.trades:
            price = t.get("price", 0)
            confidence = t.get("confidence", 0)
            code = t.get("stock", "")
            strategy = t.get("strategy", "")
            action = t.get("action", "")

            if action == "buy":
                qty = int(cash * 0.2 / max(price, 1))
                cost = qty * price
                cash -= cost
                current_price = price * (1 + (t.get("pnl", 0) / max(cost, 1)))
                mv = qty * current_price
                pnl = mv - cost
                stock_value += mv
                positions.append({
                    "stock": code, "strategy": strategy, "action": action,
                    "quantity": qty, "entry_price": price, "current_price": current_price,
                    "market_value": mv, "pnl": pnl, "pnl_pct": pnl / cost * 100 if cost > 0 else 0,
                    "weight": 0, "rsi": context.indicators.get(code, {}).get("rsi_14", "-"),
                    "status": "持仓中",
                })
                strategy_map[strategy] = strategy_map.get(strategy, 0) + 1

        total_assets = cash + stock_value
        for p in positions:
            p["weight"] = round(p["market_value"] / max(total_assets, 1) * 100, 2)

        context.position_analysis = {
            "positions": positions,
            "summary": {
                "initial_cash": INITIAL_CASH,
                "cash": round(cash, 2),
                "stock_value": round(stock_value, 2),
                "total_assets": round(total_assets, 2),
                "total_return": round((total_assets / INITIAL_CASH - 1) * 100, 2),
                "active_positions": len(positions),
                "strategy_allocation": strategy_map,
            },
        }
        return context
