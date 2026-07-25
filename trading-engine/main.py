#!/usr/bin/env python3
import queue
import random
import subprocess
import threading
from pathlib import Path

from database import init_db, save_trade

DIR = Path(__file__).parent
PRICING = DIR / "pricing"
MAX_POS = 10

position = 0
avg_cost = 0.0
realized_pnl = 0.0


def compile_pricing():
    if not PRICING.exists():
        subprocess.run(
            ["c++", "-O2", str(DIR / "pricing.cpp"), "-o", str(PRICING)], check=True
        )


def gen_prices(n=100):
    random.seed(42)
    p = 100.0
    prices = []
    for _ in range(n):
        p += random.uniform(-0.5, 0.5)
        prices.append(round(p, 2))
    return prices


def get_quote(price):
    out = subprocess.run(
        [str(PRICING), str(price)], capture_output=True, text=True, check=True
    )
    bid, ask, option = map(float, out.stdout.split())
    return bid, ask, option


def try_order(side, qty, fill):
    global position, avg_cost, realized_pnl
    if side == "BUY" and position + qty > MAX_POS:
        return "REJECTED"
    if side == "SELL" and position < qty:
        return "REJECTED"
    if side == "BUY":
        avg_cost = (avg_cost * position + fill * qty) / (position + qty)
        position += qty
    else:
        realized_pnl += (fill - avg_cost) * qty
        position -= qty
    save_trade(side, qty, fill)
    return "APPROVED"


def feed_prices(q, prices):
    for p in prices:
        q.put(p)
    q.put(None)


def main():
    compile_pricing()
    init_db()
    prices = gen_prices()
    q = queue.Queue()
    threading.Thread(target=feed_prices, args=(q, prices), daemon=True).start()
    tick = 0
    while True:
        price = q.get()
        if price is None:
            break
        bid, ask, option = get_quote(price)
        if tick == 0:
            print(f"Market Price: ${price:.2f}")
            print(f"Bid: ${bid:.2f} | Ask: ${ask:.2f}")
            print(f"Option Value: ${option:.2f} (simplified)\n")
            status = try_order("BUY", 1, ask)
            print(f"Order: BUY 1 @ ${ask:.2f}")
            print(f"Risk Check: {status}")
            print(f"Position: {position} share(s)\n")
        if tick == 5:
            try_order("SELL", 1, bid)
            print(f"Order: SELL 1 @ ${bid:.2f}")
            print(f"Position: {position} shares")
        tick += 1


if __name__ == "__main__":
    main()
