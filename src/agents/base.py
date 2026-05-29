"""Agent 基类 + 共享上下文 + 编排器（复用 A 股版本）"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentContext:
    date: str = ""
    news_data: list = field(default_factory=list)
    hot_sectors: list = field(default_factory=list)
    market_data: dict = field(default_factory=dict)
    stock_pool: list = field(default_factory=list)
    indicators: dict = field(default_factory=dict)
    ts_signals: list = field(default_factory=list)
    rl_signals: list = field(default_factory=list)
    regime: str = ""
    strategy_results: dict = field(default_factory=dict)
    backtest_results: list = field(default_factory=list)
    portfolio: dict = field(default_factory=dict)
    risk_metrics: dict = field(default_factory=dict)
    trades: list = field(default_factory=list)
    market_judgement: dict = field(default_factory=dict)
    position_analysis: dict = field(default_factory=dict)
    report_text: str = ""
    report_html: str = ""
    viz_path: str = ""
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    bus: Any = None
    db: Any = None


class BaseAgent(ABC):
    name: str = "base"
    description: str = ""

    @abstractmethod
    def execute(self, context: AgentContext) -> AgentContext:
        ...

    def publish(self, context: AgentContext, topic: str, message: Any = None):
        if context.bus is not None:
            context.bus.publish(topic, message if message is not None else self._snapshot(context))

    def consume(self, context: AgentContext, topic: str, timeout: float = None) -> Any:
        if context.bus is not None:
            return context.bus.consume(topic, timeout=timeout)
        return None

    @staticmethod
    def _snapshot(context: AgentContext) -> dict:
        return {
            "hot_sectors": context.hot_sectors,
            "ts_signals": context.ts_signals,
            "rl_signals": context.rl_signals,
            "backtest_results": context.backtest_results,
            "regime": context.regime,
            "strategy_results": context.strategy_results,
            "risk_metrics": context.risk_metrics,
            "stock_pool": context.stock_pool,
            "market_judgement": context.market_judgement,
            "trades": context.trades,
        }

    def __repr__(self) -> str:
        return f"<Agent {self.name}>"


class OrchestratorAgent(BaseAgent):
    name = "orchestrator"

    def __init__(self, agents: list, message_bus=None, database=None):
        self.agents = agents
        self.message_bus = message_bus
        self.database = database

    def execute(self, context: AgentContext) -> AgentContext:
        context.bus = self.message_bus
        context.db = self.database
        import time
        for agent in self.agents:
            if context.errors:
                context.warnings.append(f"跳过 {agent.name}（上游失败）")
                continue
            aid = agent.name
            t0 = time.time()
            try:
                context = agent.execute(context)
                topic_map = {
                    "hot_sector_mining": "sectors", "data_fetch": "market_data",
                    "ts_signal": "ts_signals", "rl_trading": "rl_signals",
                    "multi_strategy": "backtest", "risk_management": "risk",
                    "market_judgement": "market", "report_generator": "report",
                    "visualization": "viz", "feishu_push": "feishu", "storage": "storage",
                }
                topic = topic_map.get(aid)
                if topic:
                    agent.publish(context, topic)
                elapsed = int((time.time() - t0) * 1000)
                if context.db is not None:
                    context.db.save_agent_log(agent_name=aid, date=context.date, status="ok",
                                              execution_time_ms=elapsed)
                print(f"  ✓ {aid} ({elapsed}ms)")
            except Exception as e:
                elapsed = int((time.time() - t0) * 1000)
                context.errors.append(f"{aid} 失败: {e}")
                print(f"  ✗ {aid} 失败: {e} ({elapsed}ms)")
                if context.db is not None:
                    context.db.save_agent_log(agent_name=aid, date=context.date, status="error",
                                              execution_time_ms=elapsed, error=str(e))
        return context
