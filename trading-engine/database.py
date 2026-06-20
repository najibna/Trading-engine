import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "trades.db"


def init_db():
    with sqlite3.connect(DB) as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS trades (side TEXT, qty INT, price REAL)"
        )
        c.commit()


def save_trade(side, qty, price):
    with sqlite3.connect(DB) as c:
        c.execute("INSERT INTO trades VALUES (?, ?, ?)", (side, qty, price))
        c.commit()


def count_trades():
    with sqlite3.connect(DB) as c:
        return c.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
