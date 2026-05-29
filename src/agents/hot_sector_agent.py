"""热门板块挖掘 Agent — 美股版（Yahoo Finance US + CNBC + Reuters + Finviz + MarketWatch）"""
import re
import requests
from ..agents.base import AgentContext, BaseAgent
from ..data.sector_map import extract_hot_sectors_from_news, _SECTOR_STOCK_MAP_US
from ..data.fetcher import fetch_us_news

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
})


class HotSectorMiningAgent(BaseAgent):
    name = "hot_sector_mining"
    description = "从美国和中国财经媒体挖掘美股热门板块"

    def execute(self, context: AgentContext) -> AgentContext:
        all_news = []

        # 1. Yahoo Finance US
        news = self._fetch_yahoo_finance_us()
        if news:
            context.warnings.append(f"Yahoo Finance US: {len(news)} 条新闻")
            all_news.extend(news)

        # 2. CNBC
        if not all_news:
            news = self._fetch_cnbc_news()
            if news:
                context.warnings.append(f"CNBC: {len(news)} 条新闻")
                all_news.extend(news)

        # 3. Reuters
        if not all_news:
            news = self._fetch_reuters_news()
            if news:
                context.warnings.append(f"Reuters: {len(news)} 条新闻")
                all_news.extend(news)

        # 4. Finviz
        if not all_news:
            news = self._fetch_finviz_news()
            if news:
                context.warnings.append(f"Finviz: {len(news)} 条新闻")
                all_news.extend(news)

        # 5. MarketWatch
        if not all_news:
            news = self._fetch_marketwatch_news()
            if news:
                context.warnings.append(f"MarketWatch: {len(news)} 条新闻")
                all_news.extend(news)

        # 6. yfinance API
        if not all_news:
            news = fetch_us_news()
            if news:
                context.warnings.append(f"Yahoo Finance API: {len(news)} 条新闻")
                all_news.extend(news)

        # 7. 财联社（中文兜底）
        if not all_news:
            news = self._fetch_cls_news()
            if news:
                context.warnings.append(f"财联社: {len(news)} 条新闻")
                all_news.extend(news)

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

        # 预填 stock_pool（供 data_agent 使用）
        pool = []
        for s in context.hot_sectors:
            for code in s.get("stocks", []):
                if code not in pool:
                    pool.append(code)
        context.stock_pool = pool

        return context

    def _fetch_yahoo_finance_us(self) -> list:
        """从 Yahoo Finance 获取美股新闻"""
        try:
            r = _SESSION.get("https://finance.yahoo.com/news/", timeout=10)
            r.raise_for_status()
            titles = re.findall(r'<h3[^>]*>(.*?)</h3>', r.text, re.DOTALL)[:10]
            items = []
            for t in titles:
                clean = re.sub(r'<.*?>', '', t).strip()
                if clean:
                    items.append({"source": "yahoo_finance", "title": clean, "content": clean})
            return items
        except Exception:
            return []

    def _fetch_cnbc_news(self) -> list:
        """从 CNBC 获取美股新闻"""
        try:
            r = _SESSION.get("https://www.cnbc.com/markets/", timeout=10)
            r.raise_for_status()
            titles = re.findall(r'<a[^>]*class="Card-title"[^>]*>(.*?)</a>', r.text, re.DOTALL)[:10]
            items = []
            for t in titles:
                clean = re.sub(r'<.*?>', '', t).strip()
                if clean:
                    items.append({"source": "cnbc", "title": clean, "content": clean})
            return items
        except Exception:
            return []

    def _fetch_reuters_news(self) -> list:
        """从 Reuters 获取美股新闻"""
        try:
            r = _SESSION.get("https://www.reuters.com/markets/", timeout=10)
            r.raise_for_status()
            titles = re.findall(r'<h[2-4][^>]*>(.*?)</h[2-4]>', r.text, re.DOTALL)[:10]
            items = []
            for t in titles:
                clean = re.sub(r'<.*?>', '', t).strip()
                if clean and len(clean) > 20:
                    items.append({"source": "reuters", "title": clean, "content": clean})
            return items
        except Exception:
            return []

    def _fetch_finviz_news(self) -> list:
        """从 Finviz 获取美股新闻"""
        try:
            r = _SESSION.get("https://finviz.com/news.ashx", timeout=10,
                             headers={"Referer": "https://finviz.com/"})
            r.raise_for_status()
            titles = re.findall(r'<a[^>]*class="nn-tab-link"[^>]*>(.*?)</a>', r.text, re.DOTALL)[:10]
            items = []
            for t in titles:
                clean = re.sub(r'<.*?>', '', t).strip()
                if clean:
                    items.append({"source": "finviz", "title": clean, "content": clean})
            return items
        except Exception:
            return []

    def _fetch_marketwatch_news(self) -> list:
        """从 MarketWatch 获取美股新闻"""
        try:
            r = _SESSION.get("https://www.marketwatch.com/latest-news", timeout=10)
            r.raise_for_status()
            titles = re.findall(r'<h[2-4][^>]*class="article__headline"[^>]*>(.*?)</h[2-4]>',
                                r.text, re.DOTALL)[:10]
            if not titles:
                titles = re.findall(r'<a[^>]*class="link"[^>]*>(.*?)</a>', r.text, re.DOTALL)[:10]
            items = []
            for t in titles:
                clean = re.sub(r'<.*?>', '', t).strip()
                if clean:
                    items.append({"source": "marketwatch", "title": clean, "content": clean})
            return items
        except Exception:
            return []

    def _fetch_cls_news(self) -> list:
        """从财联社获取中文新闻（兜底）"""
        try:
            r = requests.get("https://www.cls.cn/api/telegraph",
                             params={"category": 1, "limit": 10}, timeout=10)
            data = r.json()
            items = []
            for roll in data.get("data", {}).get("roll_data", []):
                title = roll.get("title", "") or roll.get("content", "")
                if title:
                    items.append({"source": "cls", "title": title, "content": title})
            return items
        except Exception:
            return []

    def _preset_sectors(self) -> list[dict]:
        """兜底预设板块"""
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
