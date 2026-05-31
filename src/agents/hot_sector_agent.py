#!/usr/bin/env python3
"""热门板块挖掘 Agent — 美股版（基于 scrapling_utils）"""
from ..agents.base import AgentContext, BaseAgent
from ..data.sector_map import extract_hot_sectors_from_news, _SECTOR_STOCK_MAP_US
from ..data.fetcher import fetch_us_news
from scrapling_utils import SmartFetcher
from scrapling_utils.news_sources import (
    YahooFinanceNews, CNBCNews, ReutersNews,
    FinvizNews, MarketWatchNews, CailiansheNews,
)

_fetcher = SmartFetcher()
_yahoo = YahooFinanceNews(); _yahoo.fetcher = _fetcher
_cnbc = CNBCNews(); _cnbc.fetcher = _fetcher
_reuters = ReutersNews(); _reuters.fetcher = _fetcher
_finviz = FinvizNews(); _finviz.fetcher = _fetcher
_mw = MarketWatchNews(); _mw.fetcher = _fetcher
_cls = CailiansheNews(); _cls.fetcher = _fetcher


class HotSectorMiningAgent(BaseAgent):
    name = "hot_sector_mining"
    description = "从美国和中国财经媒体挖掘美股热门板块"

    def execute(self, context: AgentContext) -> AgentContext:
        all_news = []

        # 尝试各新闻源（遇到第一个成功的就停止）
        for source_name, src in [
            ("yahoo_finance", _yahoo),
            ("cnbc", _cnbc),
            ("reuters", _reuters),
            ("finviz", _finviz),
            ("marketwatch", _mw),
        ]:
            try:
                items = src.fetch()
                if items:
                    context.warnings.append(f"{source_name}: {len(items)} 条新闻")
                    all_news = [n.to_dict() for n in items]
                    break
            except Exception as e:
                context.warnings.append(f"{source_name} 失败: {e}")

        # 6. yfinance API
        if not all_news:
            news = fetch_us_news()
            if news:
                context.warnings.append(f"Yahoo Finance API: {len(news)} 条新闻")
                all_news = news

        # 7. 财联社（中文兜底）
        if not all_news:
            try:
                items = _cls.fetch()
                if items:
                    context.warnings.append(f"财联社: {len(items)} 条新闻")
                    all_news = [n.to_dict() for n in items]
            except Exception:
                pass

        context.news_data = all_news

        if all_news:
            sectors = extract_hot_sectors_from_news(all_news)
            if sectors:
                context.hot_sectors = sectors
            else:
                context.hot_sectors = self._preset_sectors()
                context.warnings.append("未能从新闻提取板块，使用预设板块")
        else:
            context.hot_sectors = self._preset_sectors()
            context.warnings.append("所有新闻源均不可用，使用预设板块")

        context.warnings.append(f"美股热门板块: {len(context.hot_sectors)} 个")

        pool = []
        for s in context.hot_sectors:
            for code in s.get("stocks", []):
                if code not in pool:
                    pool.append(code)
        context.stock_pool = pool

        return context

    def _preset_sectors(self) -> list[dict]:
        results = []
        heat = 85
        for sector, stocks in _SECTOR_STOCK_MAP_US.items():
            results.append({
                "sector": sector,
                "heat_score": heat,
                "summary": f"热度{heat}",
                "stocks": stocks[:6],
            })
            heat -= 5
        return results
