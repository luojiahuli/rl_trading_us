"""可视化 Agent（美股版）"""
import os
import numpy as np
import pandas as pd
from ..agents.base import AgentContext, BaseAgent


class VisualizationAgent(BaseAgent):
    name = "visualization"
    description = "生成港股分析可视化图表"

    def execute(self, context: AgentContext) -> AgentContext:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from config import REPORT_DIR
            # macOS 中文字体
            import matplotlib.font_manager as fm
            for fp in ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"]:
                try:
                    fm.fontManager.addfont(fp)
                except Exception:
                    pass
            plt.rcParams["font.sans-serif"] = ["PingFang HK", "Heiti TC", "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            os.makedirs(REPORT_DIR, exist_ok=True)

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            fig.suptitle(f"美股量化交易分析 - {context.date}", fontsize=14)

            # 1. 策略绩效
            ax1 = axes[0, 0]
            if context.strategy_results:
                perf = context.strategy_results.get("strategy_performance", {})
                if perf:
                    names = list(perf.keys())
                    returns = [perf[n].get("total_return", 0) * 100 for n in names]
                    sharps = [perf[n].get("sharpe_ratio", 0) for n in names]
                    x = np.arange(len(names))
                    ax1.bar(x - 0.2, returns, 0.4, label="收益率%", color=["#2196F3" if r > 0 else "#F44336" for r in returns])
                    ax1_twin = ax1.twinx()
                    ax1_twin.bar(x + 0.2, sharps, 0.4, label="Sharpe", color="#FF9800", alpha=0.7)
                    ax1.set_xticks(x)
                    ax1.set_xticklabels(names, rotation=15)
                    ax1.set_title("策略绩效")
                    ax1.legend(loc="upper left")
                    ax1_twin.legend(loc="upper right")

            # 2. 交易信号
            ax2 = axes[0, 1]
            if context.rl_signals:
                buys = sum(1 for s in context.rl_signals if s["action"] == "buy")
                sells = sum(1 for s in context.rl_signals if s["action"] == "sell")
                ax2.bar(["买入", "卖出"], [buys, sells], color=["#4CAF50", "#F44336"])
                ax2.set_title(f"交易信号 (共{len(context.rl_signals)}个)")
            else:
                ax2.text(0.5, 0.5, "无交易信号", ha="center", va="center", transform=ax2.transAxes)

            # 3. 板块热度
            ax3 = axes[1, 0]
            if context.hot_sectors:
                sectors = [s["sector"] for s in context.hot_sectors[:8]]
                heats = [s.get("heat_score", 50) for s in context.hot_sectors[:8]]
                ax3.barh(range(len(sectors)), heats, color="#2196F3")
                ax3.set_yticks(range(len(sectors)))
                ax3.set_yticklabels(sectors, fontsize=9)
                ax3.set_title("热门板块热度")
            else:
                ax3.text(0.5, 0.5, "无板块数据", ha="center", va="center", transform=ax3.transAxes)

            # 4. 市场状态
            ax4 = axes[1, 1]
            ax4.axis("off")
            mj = context.market_judgement or {}
            lines = [
                f"市场阶段: {mj.get('market_phase', '—')}",
                f"趋势方向: {mj.get('trend_direction', '—')}",
                f"置信度: {mj.get('confidence', '—')}",
                f"市场宽度: {mj.get('details', {}).get('stock_breadth', {}).get('pct_above_ma50', 0)}%",
                f"股票池: {len(context.stock_pool)} 只",
                f"信号: {len(context.rl_signals)} 个",
                f"回测: {len(context.backtest_results)} 次",
                f"状态: {context.regime}",
            ]
            ax4.text(0.1, 0.9, "\n".join(lines), va="top", fontsize=11, transform=ax4.transAxes)
            ax4.set_title("市场概览")

            plt.tight_layout()
            path = os.path.join(REPORT_DIR, f"us_report_{context.date}.png")
            plt.savefig(path, dpi=100, bbox_inches="tight")
            plt.close()
            context.viz_path = path
            context.warnings.append(f"可视化已保存: {path}")
        except Exception as e:
            context.warnings.append(f"可视化失败: {e}")

        return context
