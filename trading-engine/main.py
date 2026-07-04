#!/usr/bin/env python3
import random
import subprocess
from pathlib import Path

DIR = Path(__file__).parent
PRICING = DIR / "pricing"


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


def main():
    compile_pricing()
    price = gen_prices(1)[0]
    bid, ask, option = get_quote(price)
    print(f"Market Price: ${price:.2f}")
    print(f"Bid: ${bid:.2f} | Ask: ${ask:.2f}")
    print(f"Option Value: ${option:.2f} (simplified)")


if __name__ == "__main__":
    main()
