#!/usr/bin/env python3
"""美股回测报告生成：策略对比 + 权益曲线 + README 更新"""
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from config import START_DATE, END_DATE, INITIAL_CASH
from src.data.fetcher import fetch_stock_daily
from src.data.indicators import compute_indicators
from src.backtest.strategies import get_all_strategies, get_enhanced_strategies
from src.backtest.engine import BacktestEngine, PortfolioBacktestEngine
from src.data.sector_map import _SECTOR_STOCK_MAP_US

REPORT_DIR = os.path.join(os.path.dirname(__file__), "output/reports")
os.makedirs(REPORT_DIR, exist_ok=True)

END_DATE = END_DATE or datetime.today().strftime("%Y-%m-%d")


def fetch_all_data() -> dict[str, pd.DataFrame]:
    """获取所有股票的日线数据并计算指标"""
    all_codes = []
    for sector, codes in _SECTOR_STOCK_MAP_US.items():
        for code in codes:
            all_codes.append(code)
    all_codes = sorted(set(all_codes))

    market_data = {}
    for code in all_codes:
        df = fetch_stock_daily(code, start_date=START_DATE, end_date=END_DATE)
        if df is None or len(df) < 30:
            continue
        df = compute_indicators(df)
        market_data[code] = df
    return market_data


def run_backtest_group(market_data: dict, strategies: list, engine_params: dict = None) -> pd.DataFrame:
    """对多只股票逐一回测，汇总 equity_curve 合计"""
    ep = engine_params or {}
    engine = BacktestEngine(initial_cash=INITIAL_CASH, **ep)
    all_results = []

    for code, df in market_data.items():
        for strategy in strategies:
            try:
                signals = strategy.generate_signals(df)
                result = engine.run(df, signals, strategy.name)
                result["stock"] = code
                all_results.append(result)
            except Exception:
                continue

    if not all_results:
        return pd.DataFrame()

    df_results = pd.DataFrame(all_results)
    strategy_curves = {}
    for s_name in df_results["strategy"].unique():
        sub = df_results[df_results["strategy"] == s_name]
        curves = [np.array(r["equity_curve"]) for r in sub.to_dict("records")]
        min_len = min(len(c) for c in curves)
        aligned = np.array([c[:min_len] for c in curves])
        strategy_curves[s_name] = aligned.sum(axis=0).tolist()

    summary = []
    for s_name in df_results["strategy"].unique():
        sub = df_results[df_results["strategy"] == s_name]
        total_ret = sub["total_return"].sum()
        avg_sharpe = sub["sharpe_ratio"].mean()
        avg_dd = sub["max_drawdown"].mean()
        total_trades = sub["num_trades"].sum()
        summary.append({
            "strategy": s_name,
            "total_return": total_ret,
            "sharpe_ratio": avg_sharpe,
            "max_drawdown": avg_dd,
            "num_trades": total_trades,
            "n_stocks": len(sub),
        })

    df_summary = pd.DataFrame(summary)
    df_summary["equity_curve"] = df_summary["strategy"].map(strategy_curves)
    return df_summary


def run_portfolio_backtests(market_data: dict) -> pd.DataFrame:
    """使用组合引擎 PortfolioBacktestEngine 进行回测"""
    strategy_configs = {
        "basic_momentum": {"sl": 0.05, "tp": 0.15, "max_pos": 3},
        "basic_trend": {"sl": 0.05, "tp": 0.12, "max_pos": 3},
        "enhanced_momentum": {"sl": 0.04, "tp": 0.18, "max_pos": 3},
        "enhanced_trend": {"sl": 0.05, "tp": 0.12, "max_pos": 3},
        "enhanced_breakout": {"sl": 0.05, "tp": 0.15, "max_pos": 3},
        "enhanced_mean_reversion": {"sl": 0.04, "tp": 0.10, "max_pos": 3},
    }

    all_strategies = {s.name: s for s in get_all_strategies() + get_enhanced_strategies()}
    results = []

    for name, cfg in strategy_configs.items():
        if name not in all_strategies:
            continue
        engine = PortfolioBacktestEngine(
            initial_cash=INITIAL_CASH,
            max_positions=cfg["max_pos"],
            stop_loss_pct=cfg["sl"],
            take_profit_pct=cfg["tp"],
        )
        try:
            result = engine.run(market_data, all_strategies[name], name)
            results.append(result)
        except Exception:
            continue

    df_portfolio = pd.DataFrame(results) if results else pd.DataFrame()
    return df_portfolio


def generate_chart(df_basic: pd.DataFrame, df_portfolio: pd.DataFrame, output_path: str):
    """生成策略对比图"""
    n_plots = 0
    if df_basic is not None and not df_basic.empty:
        n_plots += 1
    if df_portfolio is not None and not df_portfolio.empty:
        n_plots += 1
    if n_plots == 0:
        return

    fig, axes = plt.subplots(1, n_plots, figsize=(7 * n_plots, 5))
    if n_plots == 1:
        axes = [axes]

    ax_idx = 0
    colors = plt.cm.Set1(np.linspace(0, 1, 10))

    if df_basic is not None and not df_basic.empty:
        ax = axes[ax_idx]
        for i, (_, row) in enumerate(df_basic.iterrows()):
            curve = row.get("equity_curve")
            if curve and len(curve) > 1:
                label = f"{row['strategy']} ({row['total_return']*100:.1f}%)"
                ax.plot(curve[:500], label=label, color=colors[i % len(colors)], linewidth=1.2)
        ax.set_title("Basic Strategies - Equity Curves", fontsize=12)
        ax.set_ylabel("Portfolio Value (USD)")
        ax.legend(fontsize=7, loc="upper left")
        ax.grid(True, alpha=0.3)
        ax_idx += 1

    if df_portfolio is not None and not df_portfolio.empty:
        ax = axes[ax_idx]
        for i, (_, row) in enumerate(df_portfolio.iterrows()):
            curve = row.get("equity_curve")
            if curve and len(curve) > 1:
                label = f"{row['strategy']} ({row['total_return']*100:.1f}%)"
                ax.plot(curve, label=label, color=colors[i % len(colors)], linewidth=1.2)
        ax.set_title("Portfolio Engine Strategies", fontsize=12)
        ax.set_ylabel("Portfolio Value (USD)")
        ax.legend(fontsize=7, loc="upper left")
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"Chart saved: {output_path}")


def update_readme(df_basic: pd.DataFrame, df_portfolio: pd.DataFrame, equity_csv: str, chart_rel: str):
    """更新 README.md 回测结果"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    lines = []
    try:
        with open("README.md", "r") as f:
            content = f.read()
            lines = content.split("\n")
    except FileNotFoundError:
        lines = ["# 美股量化交易系统 (US)"]

    section_start = None
    section_end = None
    for i, line in enumerate(lines):
        if "## 回测表现" in line or "## Backtest" in line:
            section_start = i
        if section_start is not None and line.startswith("## ") and i > section_start:
            section_end = i
            break
    if section_start is not None and section_end is None:
        section_end = len(lines)

    new_section = [
        "",
        "## 回测表现",
        f"更新日期: {date_str}",
        f"初始资金: ${INITIAL_CASH:,}",
        f"数据范围: {START_DATE} ~ {END_DATE}",
        "",
    ]

    if df_basic is not None and not df_basic.empty:
        new_section.append("### 基础策略 (逐只回测合计)")
        new_section.append("| 策略 | 总收益率 | Sharpe | 最大回撤 | 交易次数 |")
        new_section.append("|------|---------|--------|---------|---------|")
        for _, row in df_basic.sort_values("total_return", ascending=False).iterrows():
            new_section.append(
                f"| {row['strategy']} | {row['total_return']*100:+.2f}% | {row['sharpe_ratio']:.2f} | {row['max_drawdown']*100:.2f}% | {int(row['num_trades'])} |"
            )
        new_section.append("")

    if df_portfolio is not None and not df_portfolio.empty:
        new_section.append("### 组合引擎 (集中投资+止损止盈)")
        new_section.append("| 策略 | 总收益率 | Sharpe | 最大回撤 | 交易次数 | 止损次数 | 止盈次数 |")
        new_section.append("|------|---------|--------|---------|---------|---------|---------|")
        for _, row in df_portfolio.sort_values("total_return", ascending=False).iterrows():
            new_section.append(
                f"| {row['strategy']} | {row['total_return']*100:+.2f}% | {row['sharpe_ratio']:.2f} | {row['max_drawdown']*100:.2f}% | {int(row['num_trades'])} | {int(row.get('num_stop_loss', 0))} | {int(row.get('num_take_profit', 0))} |"
            )
        new_section.append("")

    if chart_rel:
        new_section.append(f"![Equity Curves]({chart_rel})")
        new_section.append("")

    if equity_csv:
        new_section.append(f"详细数据: [{equity_csv}]({equity_csv})")
        new_section.append("")

    if section_start is not None:
        lines = lines[:section_start] + new_section + (lines[section_end:] if section_end else [])
    else:
        lines = lines + new_section

    while lines and lines[-1] == "":
        lines.pop()
    lines.append("")

    with open("README.md", "w") as f:
        f.write("\n".join(lines))
    print("README.md updated")


def main():
    print(f"US Backtest Report Generator")
    print(f"Period: {START_DATE} ~ {END_DATE}")
    print(f"Fetching data...")
    market_data = fetch_all_data()
    print(f"Got {len(market_data)} stocks")

    print("Running basic strategies (per-stock)...")
    df_basic = run_backtest_group(market_data, get_all_strategies())
    if df_basic is not None and not df_basic.empty:
        print(f"  {len(df_basic)} strategy groups")

    print("Running portfolio strategies...")
    df_portfolio = run_portfolio_backtests(market_data)
    if df_portfolio is not None and not df_portfolio.empty:
        print(f"  {len(df_portfolio)} strategies")

    date_tag = datetime.now().strftime("%Y%m%d")
    csv_path = os.path.join(REPORT_DIR, f"equity_curves_{date_tag}.csv")
    all_dfs = []
    if df_basic is not None and not df_basic.empty:
        d = df_basic.copy()
        d["type"] = "basic"
        all_dfs.append(d)
    if df_portfolio is not None and not df_portfolio.empty:
        d = df_portfolio.copy()
        d["type"] = "portfolio"
        all_dfs.append(d)
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        max_len = max(len(r.get("equity_curve") or []) for _, r in combined.iterrows())
        csv_data = {}
        for _, row in combined.iterrows():
            curve = row.get("equity_curve") or []
            padded = curve + [curve[-1]] * (max_len - len(curve)) if curve else []
            csv_data[f"{row['type']}_{row['strategy']}"] = padded
        if csv_data:
            pd.DataFrame(csv_data).to_csv(csv_path, index=False)
            print(f"Equity curves saved: {csv_path}")

    chart_path = os.path.join(REPORT_DIR, f"backtest_chart_{date_tag}.png")
    chart_rel = f"output/reports/backtest_chart_{date_tag}.png"
    generate_chart(df_basic, df_portfolio, chart_path)

    update_readme(df_basic, df_portfolio, csv_path, chart_rel)
    print("Done!")


if __name__ == "__main__":
    main()
