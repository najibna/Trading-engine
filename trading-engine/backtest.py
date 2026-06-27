def backtest_pnl(prices):
    pos, cash = 0, 0.0
    for p in prices:
        if p <= 99.5 and pos < 10:
            cash -= p + 0.05
            pos += 1
        elif p >= 100.5 and pos > 0:
            cash += p - 0.05
            pos -= 1
    return cash + pos * prices[-1]
