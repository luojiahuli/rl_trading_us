"""美股数据获取 — yfinance + 合成数据回退"""
import numpy as np
import pandas as pd

INDEX_MAP = {"^GSPC": "标普500", "^IXIC": "纳斯达克", "^DJI": "道琼斯"}


def fetch_stock_daily(symbol: str, start_date: str = "2024-01-01",
                      end_date: str = None) -> pd.DataFrame:
    """获取美股日线数据（无后缀，如 AAPL / MSFT）"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, auto_adjust=True)
        if df.empty or len(df) < 30:
            return _generate_synthetic_us(symbol, start_date, end_date)
        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume",
        })
        df["date"] = df.index.strftime("%Y-%m-%d")
        df["pct_chg"] = df["close"].pct_change()
        df["amount"] = df["close"] * df["volume"]
        df["turnover"] = 0.0
        return df
    except Exception:
        return _generate_synthetic_us(symbol, start_date, end_date)


def fetch_index_daily(symbol: str = "^GSPC", start_date: str = "2024-01-01",
                      end_date: str = None) -> pd.DataFrame:
    """获取美股指数数据"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, auto_adjust=False)
        if df.empty or len(df) < 30:
            return _generate_synthetic_index(symbol, start_date, end_date)
        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume",
        })
        df["date"] = df.index.strftime("%Y-%m-%d")
        df["pct_chg"] = df["close"].pct_change()
        df["amount"] = 0.0
        return df
    except Exception:
        return _generate_synthetic_index(symbol, start_date, end_date)


def fetch_us_news() -> list:
    """获取美股市场新闻"""
    try:
        import yfinance as yf
        spx = yf.Ticker("^GSPC")
        items = spx.news or []
        results = []
        for item in items[:10]:
            results.append({
                "source": "yahoo_finance",
                "title": item.get("title", ""),
                "content": item.get("summary", item.get("title", "")),
                "url": item.get("link", ""),
            })
        return results
    except Exception:
        return []


def _generate_synthetic_us(symbol: str, start_date: str,
                           end_date: str) -> pd.DataFrame:
    """生成美股合成数据（GBM + 均值回归，美股价位）"""
    np.random.seed(hash(symbol) % 2**31)
    dates = pd.date_range(start=start_date, end=end_date or pd.Timestamp.today(), freq="B")
    n = len(dates)
    base_price = 50 + np.random.random() * 450  # $50-$500
    log_price = np.log(base_price)
    prices = []
    for _ in range(n):
        ret = np.random.normal(0.0005, 0.018)
        ret -= 0.0005 * (log_price - np.log(base_price))
        log_price += ret
        log_price = max(log_price, np.log(base_price * 0.3))
        log_price = min(log_price, np.log(base_price * 2.0))
        prices.append(np.exp(log_price))
    close = np.array(prices)
    open_p = close * (1 + np.random.uniform(-0.01, 0.01, n))
    high = np.maximum(open_p, close) * (1 + np.random.uniform(0, 0.02, n))
    low = np.minimum(open_p, close) * (1 - np.random.uniform(0, 0.02, n))
    volume = np.random.randint(5_000_000, 80_000_000, n)
    df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "open": open_p, "high": high, "low": low, "close": close,
        "volume": volume, "pct_chg": np.nan, "amount": close * volume,
        "turnover": 0.0,
    })
    df["pct_chg"] = df["close"].pct_change()
    return df


def _generate_synthetic_index(symbol: str, start_date: str,
                              end_date: str) -> pd.DataFrame:
    """生成美股指数合成数据"""
    np.random.seed(hash(symbol) % 2**31)
    dates = pd.date_range(start=start_date, end=end_date or pd.Timestamp.today(), freq="B")
    n = len(dates)
    base_level = {"^GSPC": 5000, "^IXIC": 16000, "^DJI": 38000}
    level = base_level.get(symbol, 5000)
    prices = [level]
    for _ in range(n - 1):
        ret = np.random.normal(0.0003, 0.012)
        prices.append(prices[-1] * (1 + ret))
    prices = np.clip(prices, level * 0.7, level * 1.5)
    close = np.array(prices)
    open_p = close * (1 + np.random.uniform(-0.005, 0.005, n))
    high = np.maximum(open_p, close) * (1 + np.random.uniform(0, 0.01, n))
    low = np.minimum(open_p, close) * (1 - np.random.uniform(0, 0.01, n))
    volume = np.random.randint(100_000_000, 1_000_000_000, n)
    df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "open": open_p, "high": high, "low": low, "close": close,
        "volume": volume, "pct_chg": np.nan, "amount": 0.0,
    })
    df["pct_chg"] = df["close"].pct_change()
    return df
