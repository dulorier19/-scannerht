import sqlite3
from typing import Any


TRADE_JOURNAL_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS trade_journal (
    trade_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    archetype TEXT NOT NULL,
    entry_price REAL NOT NULL,
    initial_stop_loss REAL NOT NULL,
    exit_price REAL NOT NULL,
    exit_reason TEXT NOT NULL,
    realized_r_multiple REAL NOT NULL,
    tp_hit_count INTEGER NOT NULL DEFAULT 0,
    stopped_after_tp INTEGER NOT NULL DEFAULT 0,
    feedback_label TEXT,
    created_at TEXT NOT NULL,
    closed_at TEXT NOT NULL
)
"""

TRADE_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS trade_events (
    id TEXT PRIMARY KEY,
    trade_id TEXT,
    user_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0
)
"""


def row_to_trade_journal_record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "trade_id": row["trade_id"],
        "user_id": int(row["user_id"]),
        "symbol": row["symbol"],
        "direction": row["direction"],
        "archetype": row["archetype"],
        "entry_price": float(row["entry_price"]),
        "initial_stop_loss": float(row["initial_stop_loss"]),
        "exit_price": float(row["exit_price"]),
        "exit_reason": row["exit_reason"],
        "realized_r_multiple": float(row["realized_r_multiple"]),
        "tp_hit_count": int(row["tp_hit_count"]),
        "stopped_after_tp": bool(row["stopped_after_tp"]),
        "feedback_label": row["feedback_label"],
        "created_at": row["created_at"],
        "closed_at": row["closed_at"],
    }


def row_to_trade_event_record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "trade_id": row["trade_id"],
        "user_id": int(row["user_id"]),
        "event_type": row["event_type"],
        "message": row["message"],
        "created_at": row["created_at"],
        "acknowledged": bool(row["acknowledged"]),
    }
