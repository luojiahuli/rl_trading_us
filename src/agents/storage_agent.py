"""持久化 Agent（港股版）"""
from ..agents.base import AgentContext, BaseAgent


class StorageAgent(BaseAgent):
    name = "storage"
    description = "持久化所有港股分析结果到 SQLite"

    def execute(self, context: AgentContext) -> AgentContext:
        if context.db is None:
            return context
        try:
            if context.hot_sectors:
                context.db.save_hot_sectors(context.date, context.hot_sectors)
            if context.rl_signals:
                context.db.save_trading_signals(context.date, context.rl_signals)
            if context.backtest_results:
                context.db.save_backtest_results(context.date, context.backtest_results, context.regime)
            context.warnings.append("港股数据已持久化")
        except Exception as e:
            context.warnings.append(f"持久化失败: {e}")
        return context
