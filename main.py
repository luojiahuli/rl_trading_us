#!/usr/bin/env python3
"""美股量化交易系统 - 主入口"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agents import AgentContext, OrchestratorAgent, build_daily_pipeline
from src.storage import DatabaseManager, MessageBus
from config import OUTPUT_DIR, REPORT_DIR, LOG_DIR, DB_PATH


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "--qa" else datetime.now().strftime("%Y-%m-%d")
    is_qa = "--qa" in sys.argv

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    bus = MessageBus()
    db = DatabaseManager(DB_PATH).connect()

    print(f"🚀 启动美股 {date_str} 量化交易分析...")
    context = AgentContext(date=date_str)
    pipeline = build_daily_pipeline()
    orchestrator = OrchestratorAgent(pipeline, message_bus=bus, database=db)
    context = orchestrator.execute(context)
    db.close()

    print(f"\n{'='*50}")
    print(f"📊 美股分析完成: {date_str}")
    print(f"  热门板块: {len(context.hot_sectors)} 个")
    print(f"  股票池: {len(context.stock_pool)} 只")
    print(f"  时间信号: {len(context.ts_signals)} 个")
    print(f"  交易信号: {len(context.rl_signals)} 个")
    print(f"  回测次数: {len(context.backtest_results)} 次")
    print(f"  市场状态: {context.regime}")
    if context.viz_path:
        print(f"  可视化: {context.viz_path}")
    print(f"{'='*50}\n")

    if context.report_text:
        print(context.report_text)

    if is_qa:
        print("\n💬 问答模式已启动（请输入问题，输入 exit 退出）")
        while True:
            q = input("\n提问: ").strip()
            if q.lower() in ("exit", "quit"):
                break
            ans_parts = []
            if context.hot_sectors:
                ans_parts.append(f"今日美股热门板块: {', '.join(s['sector'] for s in context.hot_sectors[:5])}")
            if context.rl_signals:
                ans_parts.append(f"交易信号: {len(context.rl_signals)} 个")
            if context.market_judgement:
                mj = context.market_judgement
                ans_parts.append(f"市场: {mj.get('market_phase', '—')}/{mj.get('trend_direction', '—')}")
            print(f"回答: {' | '.join(ans_parts) if ans_parts else '暂无数据'}")


if __name__ == "__main__":
    main()
