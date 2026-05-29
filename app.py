#!/usr/bin/env python3
"""美股量化交易系统 - Gradio Web UI"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gradio as gr
import pandas as pd

from src.agents import AgentContext, OrchestratorAgent, build_daily_pipeline
from src.storage import DatabaseManager, MessageBus
from config import REPORT_DIR, LOG_DIR, OUTPUT_DIR, DB_PATH

_qa_context = None


def run_analysis(date_str: str):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    bus = MessageBus()
    db = DatabaseManager(DB_PATH).connect()
    context = AgentContext(date=date_str)
    pipeline = build_daily_pipeline()
    orchestrator = OrchestratorAgent(pipeline, message_bus=bus, database=db)
    context = orchestrator.execute(context)
    db.close()

    global _qa_context
    _qa_context = context

    report_text = context.report_text or "无报告数据"
    viz_html = ""
    if context.viz_path and os.path.exists(context.viz_path):
        viz_html = f'<img src="file/{context.viz_path}" style="max-width:100%"/>'

    pos = context.position_analysis or {}
    positions = pos.get("positions", [])
    summary = pos.get("summary", {})
    if positions:
        pos_df = pd.DataFrame([{
            "股票": p.get("stock", ""), "策略": p.get("strategy", ""),
            "方向": p.get("action", ""), "数量": p.get("quantity", 0),
            "均价": p.get("entry_price", 0), "现价": p.get("current_price", 0),
            "市值": p.get("market_value", 0), "盈亏": p.get("pnl", 0),
            "盈亏%": p.get("pnl_pct", 0), "RSI": p.get("rsi", "-"),
            "状态": p.get("status", ""),
        } for p in positions])
    else:
        pos_df = pd.DataFrame()
    s = summary
    overview = {
        "💰 初始资金": f"${s.get('initial_cash', 0):,.0f}",
        "💵 剩余现金": f"${s.get('cash', 0):,.2f}",
        "📊 持仓市值": f"${s.get('stock_value', 0):,.2f}",
        "🏦 总资产": f"${s.get('total_assets', 0):,.2f}",
        "📈 总收益率": f"{s.get('total_return', 0):+.2f}%",
        "📊 持仓数量": f"{s.get('active_positions', 0)} 只",
    }
    return report_text, viz_html, pos_df, overview


def refresh_positions():
    ctx = _qa_context
    if not ctx or not ctx.position_analysis:
        return "⚠️ 请先运行分析", pd.DataFrame(), {"提示": "无数据"}
    pos = ctx.position_analysis
    positions = pos.get("positions", [])
    summary = pos.get("summary", {})
    if positions:
        df = pd.DataFrame([{
            "股票": p.get("stock", ""), "策略": p.get("strategy", ""),
            "方向": p.get("action", ""), "数量": p.get("quantity", 0),
            "均价": p.get("entry_price", 0), "现价": p.get("current_price", 0),
            "市值": p.get("market_value", 0), "盈亏": p.get("pnl", 0),
            "盈亏%": p.get("pnl_pct", 0), "RSI": p.get("rsi", "-"),
            "状态": p.get("status", ""),
        } for p in positions])
    else:
        df = pd.DataFrame()
    s = summary
    overview = {
        "💰 初始资金": f"${s.get('initial_cash', 0):,.0f}",
        "💵 剩余现金": f"${s.get('cash', 0):,.2f}",
        "📊 持仓市值": f"${s.get('stock_value', 0):,.2f}",
        "🏦 总资产": f"${s.get('total_assets', 0):,.2f}",
        "📈 总收益率": f"{s.get('total_return', 0):+.2f}%",
        "📊 持仓数量": f"{s.get('active_positions', 0)} 只",
    }
    return f"✅ 已刷新（{s.get('active_positions', 0)} 只持仓中）", df, overview


def answer_question(question: str, history: list):
    if not question.strip():
        return "", history or []
    if history is None:
        history = []
    ctx = _qa_context
    if not ctx:
        reply = "请先在「运行分析」标签页执行分析管线。"
    else:
        parts = []
        if ctx.hot_sectors:
            parts.append(f"今日美股热门板块: {', '.join(s['sector'] for s in ctx.hot_sectors[:5])}")
        if ctx.rl_signals:
            parts.append(f"交易信号: {len(ctx.rl_signals)} 个")
        if ctx.market_judgement:
            mj = ctx.market_judgement
            parts.append(f"市场: {mj.get('market_phase','—')}/{mj.get('trend_direction','—')}")
        reply = " | ".join(parts) if parts else "暂无分析数据"
    history.append((question, reply))
    return "", history


with gr.Blocks(title="美股量化交易系统") as demo:
    gr.Markdown("# 🚀 美股量化交易系统\n基于多智能体架构的美股每日动态机会点挖掘")

    with gr.Tab("📊 运行分析"):
        with gr.Row():
            date_input = gr.Textbox(label="分析日期", value=datetime.now().strftime("%Y-%m-%d"), scale=3)
            run_btn = gr.Button("▶ 运行分析", variant="primary", scale=1, min_width=160)
        status = gr.Markdown("💡 点击上方按钮开始分析管线")
        report = gr.Markdown(label="分析报告")
        viz = gr.HTML(label="可视化图表")

    with gr.Tab("💰 持仓明细"):
        summary_json = gr.JSON(label="持仓摘要")
        pos_table = gr.DataFrame(label="持仓明细", wrap=True)
        with gr.Row():
            refresh_btn = gr.Button("🔄 刷新持仓", variant="secondary")
            pos_hint = gr.Markdown("💡 请先运行分析管线")

    with gr.Tab("💬 智能问答"):
        chatbot = gr.Chatbot(label="对话", height=400)
        with gr.Row():
            q_input = gr.Textbox(label="输入问题", placeholder="例如：今天哪些板块有机会？", scale=4)
            send_btn = gr.Button("发送", variant="primary", scale=1, min_width=100)
        clear_btn = gr.Button("清空对话", variant="secondary", size="sm")

    def on_run(date_str):
        yield "⏳ 正在执行美股分析管线...", "", "", {"status": "running"}
        try:
            report, viz_h, pos_df, summary = run_analysis(date_str)
            yield "✅ 美股分析完成", report, viz_h, pos_df, summary
        except Exception as e:
            yield f"❌ 失败: {e}", f"❌ 错误: {e}", "", {"error": str(e)}

    run_btn.click(fn=on_run, inputs=date_input, outputs=[status, report, viz, pos_table, summary_json])
    refresh_btn.click(fn=refresh_positions, outputs=[pos_hint, pos_table, summary_json])
    send_btn.click(fn=answer_question, inputs=[q_input, chatbot], outputs=[q_input, chatbot])
    q_input.submit(fn=answer_question, inputs=[q_input, chatbot], outputs=[q_input, chatbot])
    clear_btn.click(fn=lambda: [], outputs=[chatbot])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="美股量化交易系统 Web UI")
    parser.add_argument("--port", type=int, default=7862, help="端口号")
    parser.add_argument("--share", action="store_true", help="创建公网链接")
    args = parser.parse_args()
    demo.launch(server_port=args.port, share=args.share, theme=gr.themes.Soft(), css="footer{display:none !important}")
