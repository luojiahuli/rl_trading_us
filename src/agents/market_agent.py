"""美股市场研判 Agent — 标普500 + 纳斯达克 + 道琼斯"""
from ..agents.base import AgentContext, BaseAgent
from ..data.fetcher import fetch_index_daily
from ..data.indicators import compute_indicators, compute_volatility


class MarketJudgementAgent(BaseAgent):
    name = "market_judgement"
    description = "基于标普500/纳斯达克/道琼斯的美股市场研判"

    def execute(self, context: AgentContext) -> AgentContext:
        indices = {"标普500": "^GSPC", "纳斯达克": "^IXIC", "道琼斯": "^DJI"}
        index_data = {}

        for name, symbol in indices.items():
            df = fetch_index_daily(symbol)
            if df is not None and len(df) > 30:
                index_data[name] = df

        if not index_data:
            context.warnings.append("美股指数数据获取失败")
            return context

        primary = index_data.get("标普500", next(iter(index_data.values())))
        last = primary.iloc[-1]
        ind = compute_indicators(primary).iloc[-1]

        # 趋势方向
        ma20 = ind.get("ma20", last["close"])
        ma60 = ind.get("ma60", last["close"])
        close = last["close"]
        if close > ma20 and close > ma60:
            trend = "up"
        elif close < ma20 and close < ma60:
            trend = "down"
        else:
            trend = "sideways"

        # 市场阶段
        ret_60d = (close / primary["close"].iloc[-min(60, len(primary))] - 1) if len(primary) >= 60 else 0
        if ret_60d > 0.08:
            phase = "牛市"
        elif ret_60d < -0.08:
            phase = "熊市"
        else:
            phase = "震荡"

        # 技术指标
        rsi = ind.get("rsi_14", 50)
        vol = compute_volatility(primary)
        price_vs_ma200 = (close / ind.get("ma200", close) - 1) * 100 if "ma200" in ind else 0

        # 市场宽度
        breadth = {"pct_above_ma50": 0, "total_stocks": 0}
        if context.indicators:
            above = 0
            total = 0
            for code, ind_dict in context.indicators.items():
                ma50 = ind_dict.get("ma50")
                if ma50 and code in context.market_data:
                    total += 1
                    cp = context.market_data[code]["close"].iloc[-1]
                    if cp > ma50:
                        above += 1
            if total > 0:
                breadth = {"pct_above_ma50": round(above / total * 100, 1), "total_stocks": total}

        context.market_judgement = {
            "market_phase": phase,
            "trend_direction": trend,
            "policy_outlook": "中性",
            "confidence": "medium",
            "next_trend": f"美股处于{phase}，{trend}趋势",
            "summary": (
                f"标普500{close:.0f}点，RSI={rsi:.1f}，"
                f"价格vsMA200={price_vs_ma200:.1f}%。"
                f"市场宽度{breadth['pct_above_ma50']}%股票站上MA50。"
                f"综合判断市场处于{phase}，{trend}趋势。"
            ),
            "details": {
                "stock_breadth": breadth,
                "sector_breadth": {"breadth": "moderate", "total_sectors": len(index_data)},
                "index_trend": {
                    "price_vs_ma200_pct": round(price_vs_ma200, 1),
                    "ma_alignment": "bullish" if trend == "up" else "bearish" if trend == "down" else "mixed",
                    "rsi_14": round(rsi, 1),
                    "volatility": round(vol * 100, 1),
                },
            },
        }

        context.warnings.append(f"美股市场研判: {phase}/{trend}")
        return context
