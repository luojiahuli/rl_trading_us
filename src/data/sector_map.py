"""美股 GICS 板块映射 — 英中双语关键词 + S&P 500 成分股"""
import re

SECTOR_KEYWORDS = {
    "科技": [
        "科技", "Technology", "Software", "Semiconductor", "AI", "Cloud",
        "Chip", "Internet", "SaaS", "Cybersecurity", "Data Center",
        "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "ORCL", "CRM", "ADBE", "AMD",
    ],
    "医疗保健": [
        "医疗", "Healthcare", "Biotech", "Pharma", "Medical Device",
        "Health Insurance", "Life Sciences", "Clinical", "Therapy", "Drug",
        "UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "ABT", "MDT", "DHR", "AMGN",
    ],
    "金融": [
        "金融", "Finance", "Bank", "Investment", "Insurance", "Wealth Management",
        "FinTech", "Payment", "Capital Markets", "Mortgage", "Credit",
        "JPM", "BAC", "GS", "V", "MA", "WFC", "MS", "C", "BLK", "SCHW",
    ],
    "非必需消费": [
        "消费", "Consumer", "Retail", "E-Commerce", "Automotive", "Luxury",
        "Restaurant", "Travel", "Leisure", "Entertainment", "Casino",
        "AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "BKNG", "RCL",
    ],
    "必需消费": [
        "必需消费", "Consumer Staples", "Food", "Beverage", "Tobacco",
        "Household", "Personal Care", "Grocery", "Packaged Goods", "Beverages",
        "PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "KMB", "EL",
    ],
    "能源": [
        "能源", "Energy", "Oil", "Gas", "Petroleum", "Refining", "Pipeline",
        "Drilling", "Exploration", "Renewable Energy", "Offshore",
        "XOM", "CVX", "COP", "SLB", "EOG", "PSX", "MPC", "VLO", "OXY", "HES",
    ],
    "工业": [
        "工业", "Industrial", "Manufacturing", "Aerospace", "Defense",
        "Logistics", "Transportation", "Engineering", "Machinery", "Aviation",
        "CAT", "GE", "BA", "HON", "RTX", "UPS", "UNP", "LMT", "ADP", "WM",
    ],
    "公用事业": [
        "公用", "Utilities", "Electric", "Power", "Renewable", "Water",
        "Gas Utility", "Nuclear", "Clean Energy",
        "NEE", "DUK", "SO", "D", "AEP", "SRE", "EXC", "XEL", "PEG", "ED",
    ],
    "通信服务": [
        "通信", "Telecom", "Media", "Entertainment", "Streaming",
        "Social Media", "Advertising", "Broadcasting", "Telecommunications",
        "DIS", "NFLX", "T", "VZ", "CMCSA", "CHTR", "TMUS", "WBD", "PARA", "NYT",
    ],
    "房地产": [
        "房地产", "Real Estate", "REIT", "Property", "Commercial Real Estate",
        "Industrial REIT", "Residential", "Office", "Data Center REIT",
        "PLD", "AMT", "CCI", "EQIX", "SPG", "PSA", "O", "WELL", "AVB", "BXP",
    ],
}

_SECTOR_STOCK_MAP_US = {
    "科技": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "ORCL", "CRM", "ADBE", "AMD"],
    "医疗保健": ["UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "ABT", "MDT", "DHR", "AMGN"],
    "金融": ["JPM", "BAC", "GS", "V", "MA", "WFC", "MS", "C", "BLK", "SCHW"],
    "非必需消费": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "BKNG", "RCL"],
    "必需消费": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "KMB", "EL"],
    "能源": ["XOM", "CVX", "COP", "SLB", "EOG", "PSX", "MPC", "VLO", "OXY", "HES"],
    "工业": ["CAT", "GE", "BA", "HON", "RTX", "UPS", "UNP", "LMT", "ADP", "WM"],
    "公用事业": ["NEE", "DUK", "SO", "D", "AEP", "SRE", "EXC", "XEL", "PEG", "ED"],
    "通信服务": ["DIS", "NFLX", "T", "VZ", "CMCSA", "CHTR", "TMUS", "WBD", "PARA", "NYT"],
    "房地产": ["PLD", "AMT", "CCI", "EQIX", "SPG", "PSA", "O", "WELL", "AVB", "BXP"],
}

EXCLUDED_KEYWORDS: list[str] = []


def map_keywords_to_sectors(keywords: list[str]) -> list[str]:
    """将关键词列表映射到板块列表（大小写不敏感）"""
    sectors = []
    for kw in keywords:
        kw_lower = kw.lower()
        for sector, kw_list in SECTOR_KEYWORDS.items():
            if any(k.lower() == kw_lower for k in kw_list):
                if sector not in sectors:
                    sectors.append(sector)
    return sectors


def extract_hot_sectors_from_news(news_items: list[dict]) -> list[dict]:
    """从新闻列表中提取热门板块及热度"""
    all_texts = []
    for item in news_items:
        parts = []
        for key in ("title", "content", "summary", "source"):
            val = item.get(key, "")
            if isinstance(val, str):
                parts.append(val)
        all_texts.append(" ".join(parts))
    full_text = " ".join(all_texts)

    words = re.findall(r"[一-鿿]{2,}|[a-zA-Z]{3,}", full_text)
    word_set = set(w.lower() for w in words)

    sector_scores = {}
    for sector, kw_list in SECTOR_KEYWORDS.items():
        score = 0
        for kw in kw_list:
            if kw.lower() in word_set:
                score += 1
        if score > 0:
            sector_scores[sector] = score

    if not sector_scores:
        return _fallback_sectors()

    max_score = max(sector_scores.values())
    results = []
    for sector, score in sorted(sector_scores.items(), key=lambda x: -x[1]):
        heat = max(10, int(score / max_score * 100))
        stocks = get_sector_stock_codes(sector)
        results.append({
            "sector": sector,
            "heat_score": heat,
            "summary": f"热度{heat}",
            "stocks": stocks,
        })
    return results[:8]


def get_sector_stock_codes(sector_name: str, max_count: int = 10) -> list[str]:
    """获取某板块的美股股票代码列表"""
    codes = _SECTOR_STOCK_MAP_US.get(sector_name, [])
    return codes[:max_count]


def _fallback_sectors() -> list[dict]:
    """兜底：返回所有板块等热度"""
    results = []
    heat = 80
    for sector, stocks in _SECTOR_STOCK_MAP_US.items():
        results.append({
            "sector": sector,
            "heat_score": heat,
            "summary": f"热度{heat}",
            "stocks": stocks[:10],
        })
        heat -= 5
    return results
