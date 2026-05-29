"""SQLite 数据库管理器（复用 A 股版本）"""
import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn: sqlite3.Connection | None = None

    def connect(self):
        if self.conn is not None:
            return self
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()
        return self

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _init_tables(self):
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, agent_name TEXT NOT NULL,
            date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ok',
            input_summary TEXT, output_summary TEXT,
            execution_time_ms INTEGER, error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS hot_sectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            sector TEXT NOT NULL, heat_score REAL, source TEXT,
            stocks_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS trading_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            stock TEXT NOT NULL, signal_type TEXT DEFAULT 'rl',
            action TEXT NOT NULL, confidence REAL, reason TEXT,
            ts_signal_window TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            strategy_name TEXT NOT NULL, total_return REAL,
            sharpe_ratio REAL, max_drawdown REAL, num_trades INTEGER,
            regime TEXT, params_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS model_labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            model_name TEXT NOT NULL, label_type TEXT NOT NULL,
            label_value TEXT NOT NULL, confidence REAL,
            features_json TEXT, is_effective INTEGER DEFAULT 1,
            verified_by TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS market_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL, date TEXT NOT NULL,
            data_type TEXT NOT NULL DEFAULT 'daily', data_json TEXT,
            expires_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stock_code, date, data_type))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            stock TEXT NOT NULL, action TEXT NOT NULL, price REAL,
            quantity INTEGER, pnl REAL, signal_confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        index_map = {
            "agent_logs_date": "agent_logs",
            "hot_sectors_date": "hot_sectors",
            "trading_signals_date": "trading_signals",
            "backtest_date": "backtest_results",
            "model_labels_date": "model_labels",
            "trade_journal_date": "trade_journal",
        }
        for idx_name, tbl in index_map.items():
            cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{idx_name} ON {tbl}(date)")
        self.conn.commit()

    def save_agent_log(self, agent_name, date, status="ok", input_summary="",
                       output_summary="", execution_time_ms=0, error=""):
        self.conn.execute(
            "INSERT INTO agent_logs(agent_name,date,status,input_summary,output_summary,execution_time_ms,error) "
            "VALUES(?,?,?,?,?,?,?)",
            (agent_name, date, status, input_summary[:500], output_summary[:500], execution_time_ms, error))
        self.conn.commit()

    def save_hot_sectors(self, date, sectors):
        for s in sectors:
            self.conn.execute(
                "INSERT INTO hot_sectors(date,sector,heat_score,source,stocks_json) VALUES(?,?,?,?,?)",
                (date, s["sector"], s.get("heat_score", 0), s.get("summary", ""),
                 json.dumps(s.get("stocks", []), ensure_ascii=False)))
        self.conn.commit()

    def save_trading_signals(self, date, signals):
        for s in signals:
            self.conn.execute(
                "INSERT INTO trading_signals(date,stock,signal_type,action,confidence,reason,ts_signal_window) "
                "VALUES(?,?,?,?,?,?,?)",
                (date, s.get("stock", ""), s.get("signal_type", "rl"), s.get("action", ""),
                 s.get("confidence", 0), s.get("reason", ""), json.dumps(s.get("ts_signal_window", {}))))
        self.conn.commit()

    def save_backtest_results(self, date, results, regime=""):
        for r in results:
            self.conn.execute(
                "INSERT INTO backtest_results(date,strategy_name,total_return,sharpe_ratio,"
                "max_drawdown,num_trades,regime,params_json) VALUES(?,?,?,?,?,?,?,?)",
                (date, r.get("strategy", ""), r.get("total_return", 0), r.get("sharpe_ratio", 0),
                 r.get("max_drawdown", 0), r.get("num_trades", 0), regime,
                 json.dumps({k: v for k, v in r.items() if k in ("total_return", "sharpe_ratio", "max_drawdown", "num_trades")})))
        self.conn.commit()

    def save_model_label(self, date, model_name, label_type, label_value, confidence=0,
                         features=None, is_effective=True, verified_by=""):
        self.conn.execute(
            "INSERT INTO model_labels(date,model_name,label_type,label_value,confidence,"
            "features_json,is_effective,verified_by) VALUES(?,?,?,?,?,?,?,?)",
            (date, model_name, label_type, label_value, confidence,
             json.dumps(features or {}, ensure_ascii=False), 1 if is_effective else 0, verified_by))
        self.conn.commit()

    def save_trade_journal(self, date, trades):
        for t in trades:
            self.conn.execute(
                "INSERT INTO trade_journal(date,stock,action,price,quantity,pnl,signal_confidence) "
                "VALUES(?,?,?,?,?,?,?)",
                (date, t.get("stock", ""), t.get("action", ""), t.get("price", 0),
                 t.get("quantity", 0), t.get("pnl", 0), t.get("confidence", 0)))
        self.conn.commit()

    def get_hot_sectors(self, date, limit=10):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM hot_sectors WHERE date=? ORDER BY heat_score DESC LIMIT ?", (date, limit)).fetchall()]

    def get_trading_signals(self, date, action=None):
        if action:
            rows = self.conn.execute("SELECT * FROM trading_signals WHERE date=? AND action=? ORDER BY confidence DESC", (date, action))
        else:
            rows = self.conn.execute("SELECT * FROM trading_signals WHERE date=? ORDER BY confidence DESC", (date,))
        return [dict(r) for r in rows.fetchall()]

    def get_backtest_results(self, date):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM backtest_results WHERE date=? ORDER BY sharpe_ratio DESC", (date,)).fetchall()]

    def get_trade_journal(self, date=None, limit=50):
        if date:
            rows = self.conn.execute("SELECT * FROM trade_journal WHERE date=? ORDER BY created_at DESC LIMIT ?", (date, limit))
        else:
            rows = self.conn.execute("SELECT * FROM trade_journal ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows.fetchall()]

    def table_stats(self):
        stats = {}
        for table in ("agent_logs", "hot_sectors", "trading_signals", "backtest_results", "model_labels", "market_cache"):
            row = self.conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
            stats[table] = row["cnt"]
        return stats
