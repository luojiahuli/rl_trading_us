"""交易流水记录 Agent（港股版）"""
from ..agents.base import AgentContext, BaseAgent


class TradeJournalAgent(BaseAgent):
    name = "trade_journal"
    description = "记录港股交易流水"

    def execute(self, context: AgentContext) -> AgentContext:
        trades = [{
            "stock": s["stock"],
            "action": s["action"],
            "price": s.get("price", 0),
            "quantity": 0,
            "pnl": 0,
            "confidence": s.get("confidence", 0),
        } for s in context.rl_signals]

        context.trades = trades
        if context.db:
            context.db.save_trade_journal(context.date, trades)
        return context
