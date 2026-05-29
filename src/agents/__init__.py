"""美股多智能体框架 + 所有 Agent"""
from .base import AgentContext, BaseAgent, OrchestratorAgent
from .hot_sector_agent import HotSectorMiningAgent
from .data_agent import DataFetchAgent
from .ts_signal_agent import TimeSeriesSignalAgent
from .rl_agent import RLTradingAgent
from .strategy_agent import MultiStrategyAgent
from .risk_agent import RiskManagementAgent
from .market_agent import MarketJudgementAgent
from .report_agent import ReportGeneratorAgent
from .viz_agent import VisualizationAgent
from .feishu_agent import FeishuPushAgent
from .storage_agent import StorageAgent
from .trade_journal_agent import TradeJournalAgent
from .position_agent import PositionAnalysisAgent


def build_daily_pipeline() -> list:
    return [
        HotSectorMiningAgent(),
        DataFetchAgent(),
        TimeSeriesSignalAgent(),
        RLTradingAgent(),
        MultiStrategyAgent(),
        RiskManagementAgent(),
        MarketJudgementAgent(),
        ReportGeneratorAgent(),
        VisualizationAgent(),
        FeishuPushAgent(),
        TradeJournalAgent(),
        PositionAnalysisAgent(),
        StorageAgent(),
    ]


__all__ = [
    "AgentContext", "BaseAgent", "OrchestratorAgent",
    "HotSectorMiningAgent", "DataFetchAgent", "TimeSeriesSignalAgent",
    "RLTradingAgent", "MultiStrategyAgent", "RiskManagementAgent",
    "MarketJudgementAgent", "ReportGeneratorAgent", "VisualizationAgent",
    "FeishuPushAgent", "StorageAgent", "TradeJournalAgent",
    "PositionAnalysisAgent", "build_daily_pipeline",
]
