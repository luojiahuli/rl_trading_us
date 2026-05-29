"""风控管理 Agent（港股版，复用 A 股逻辑）"""
from ..agents.base import AgentContext, BaseAgent
from ..risk.manager import RiskManager


class RiskManagementAgent(BaseAgent):
    name = "risk_management"
    description = "风险管理 - 港股"

    def execute(self, context: AgentContext) -> AgentContext:
        rm = RiskManager(initial_cash=100000)
        total_value = 100000
        for t in context.trades:
            total_value += t.get("pnl", 0)
        dd = rm.check_drawdown(total_value)
        context.risk_metrics = {"drawdown": dd}
        context.warnings.append(dd["message"])
        return context
