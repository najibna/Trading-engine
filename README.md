# 📈 Trading Engine

A small **Python + C++** program that simulates how trading software handles price updates: quote them, check rules, record trades, replay history, and measure speed. Optional second script splits **market data** and **pricing** into two processes on TCP.

🔒 No real broker. No live market. All prices and trades are generated in code.

---

## 📑 Table of contents

1. [🤔 Glossary](#-glossary)
2. [🗺️ Repo map](#️-repo-map)
3. [🐍 `main.py` (every line explained)](#-mainpy-every-line-explained)
4. [⚡ `pricing.cpp` (every line explained)](#-pricingcpp-every-line-explained)
5. [💾 `database.py` (every part explained)](#-databasepy-every-part-explained)
6. [📉 `backtest.py` (every part explained)](#-backtestpy-every-part-explained)
7. [🌐 `distributed_demo.py` (every part explained)](#-distributed_demopy-every-part-explained)
8. [🙈 `.gitignore`](#-gitignore)
9. [▶️ How to run](#️-how-to-run)
10. [📺 Output (every printed line)](#-output-every-printed-line)
11. [❓ FAQ](#-faq)

---

## 🤔 Glossary

| Word | Meaning in this repo |
|------|----------------------|
| **Tick** | One price update (one loop in `main.py`). |
| **Spot / market price** | The fake current stock price for that tick. |
| **Bid** | Best buy price from the market side; you **sell** here. |
| **Ask** | Best sell price from the market side; you **buy** here. |
| **Spread** | `ask - bid` (here always **$0.10**). |
| **Position** | Shares you hold (`position` variable). |
| **Fill price** | Price used for the simulated trade (`ask` for BUY, `bid` for SELL). |
| **Realized P/L** | Profit/loss locked in when you sell (`realized_pnl`). |
| **Backtest P/L** | Separate P/L from replaying all prices in `backtest.py`. |
| **Latency** | Nanoseconds spent inside `get_quote()` per tick, shown as ms average. |
| **Queue** | Thread-safe FIFO buffer between feed thread and main thread. |
| **Daemon thread** | Background thread that exits when the main program exits. |
| **Subprocess** | Separate OS process (used to run `./pricing`). |
| **SQLite** | File database `trades.db` with a simple `trades` table. |
| **TCP** | Network protocol; used on `127.0.0.1:5555` only (your machine). |
| **JSON line** | One JSON object per line, e.g. `{"price": 100.14}`. |

---

## 🗺️ Repo map

```
Trading-engine/          ← GitHub repo root
├── main.py              ← Main simulation
├── pricing.cpp          ← C++ source for quotes
├── database.py          ← SQLite helpers
├── backtest.py          ← P/L replay function
├── distributed_demo.py  ← Two-process TCP version
├── .gitignore           ← Ignores build + DB artifacts
├── README.md            ← This file
├── pricing              ← Built by C++ (not in git)
└── trades.db            ← Created at run time (not in git)
```

**Runtime flow (local):**

```
gen_prices → queue → get_quote(pricing) → try_order → save_trade → trades.db
                              ↓
                         latencies[]
                              ↓
                    backtest_pnl(prices) + print stats
```

---

## 🐍 `main.py` (every line explained)

### 📦 Imports (lines 1–10)

| Import | Why it is here |
|--------|----------------|
| `queue` | `queue.Queue()` holds prices between threads. |
| `random` | Random walk for fake prices in `gen_prices()`. |
| `subprocess` | Runs `./pricing` and compiles C++ in `compile_pricing()`. |
| `threading` | Starts `feed_prices` on a second thread. |
| `Path` | Finds folder paths for `pricing.cpp` and binary. |
| `perf_counter_ns` | High-resolution timer around C++ calls. |
| `backtest_pnl` | Called once at end for summary P/L. |
| `count_trades`, `init_db`, `save_trade` | SQLite setup and writes. |

`#!/usr/bin/env python3` lets you run `./main.py` on Unix if the file is executable.

---

### 🔢 Module constants (lines 12–14)

| Name | Value | Meaning |
|------|-------|---------|
| `DIR` | Folder containing `main.py` | Base path for C++ files. |
| `PRICING` | `DIR / "pricing"` | Path to compiled C++ executable. |
| `MAX_POS` | `10` | Max shares you can hold (risk limit). |

---

### 🌐 Module globals (lines 16–19)

| Name | Start value | Updated when | Meaning |
|------|-------------|--------------|---------|
| `position` | `0` | `try_order()` | Shares owned now. |
| `avg_cost` | `0.0` | On each **BUY** | Average price paid for current shares. |
| `realized_pnl` | `0.0` | On each **SELL** | Running closed P/L. |
| `latencies` | `[]` | Each tick in `main()` | List of nanoseconds for each `get_quote()`. |

These are **module-level globals** (simple style for a small script).

---

### `compile_pricing()` (lines 22–26)

| Step | What happens |
|------|----------------|
| 1 | If `./pricing` already exists, do nothing. |
| 2 | Else run shell command: `c++ -O2 pricing.cpp -o pricing`. |
| `-O2` | Compiler optimization (faster binary). |
| `check=True` | Crash with error if compile fails. |

---

### `gen_prices(n=100)` (lines 29–36)

| Step | What happens |
|------|----------------|
| `random.seed(42)` | Same random sequence every run (repeatable prices). |
| `p = 100.0` | Start near $100. |
| Loop `n` times | `p += random.uniform(-0.5, 0.5)` then `round(p, 2)`. |
| Return | List of `n` floats, e.g. 100 prices. |

So each price is a **random walk** with steps between -$0.50 and +$0.50.

---

### `get_quote(price)` (lines 39–44)

| Step | What happens |
|------|----------------|
| 1 | Run `[PRICING, str(price)]` as subprocess. |
| 2 | `capture_output=True` grabs stdout. |
| 3 | `text=True` decodes stdout as string. |
| 4 | `check=True` raises if C++ exits with error. |
| 5 | Split stdout on spaces → 3 floats: **bid, ask, option**. |
| 6 | Return tuple `(bid, ask, option)`. |

**Note:** `option` is computed in C++ but only **printed** on tick 0 in `main()`; it is not used for trading logic.

---

### `try_order(side, qty, fill)` (lines 47–60)

**Parameters:**

| Param | Type | Meaning |
|-------|------|---------|
| `side` | `"BUY"` or `"SELL"` | Direction. |
| `qty` | int | Shares (always `1` in sample orders). |
| `fill` | float | Execution price (ask or bid). |

**Logic order:**

```
1. If BUY and position + qty > MAX_POS → return "REJECTED" (no DB write)
2. If SELL and position < qty           → return "REJECTED"
3. If BUY:
     avg_cost = (avg_cost * position + fill * qty) / (position + qty)
     position += qty
4. If SELL:
     realized_pnl += (fill - avg_cost) * qty
     position -= qty
5. save_trade(side, qty, fill)
6. return "APPROVED"
```

**Important:** Rejected orders do **not** call `save_trade()`.

---

### `feed_prices(q, prices)` (lines 63–66)

| Step | What happens |
|------|----------------|
| For each `p` in `prices` | `q.put(p)` |
| After all prices | `q.put(None)` = **stop signal** for main loop |

Runs on **Thread 1** (daemon).

---

### `main()` (lines 69–109)

| Line block | What happens |
|------------|----------------|
| `compile_pricing()` | Ensure `./pricing` exists. |
| `init_db()` | Reset/create SQLite table (see `database.py`). |
| `prices = gen_prices()` | 100 prices, seed 42. |
| `q = queue.Queue()` | Shared queue. |
| `threading.Thread(..., daemon=True).start()` | Start feed thread. |
| `tick = 0` | Counter for which price we are on (0-based). |

**Main loop:**

| Step | Code | Meaning |
|------|------|---------|
| Wait for price | `price = q.get()` | Blocks until feed sends a price. |
| Stop | `if price is None: break` | Feed finished. |
| Time C++ | `t0 = perf_counter_ns()` | Start timer. |
| Quote | `bid, ask, option = get_quote(price)` | Call C++. |
| Save timing | `latencies.append(...)` | Store duration in ns. |

**Tick 0 only:**

| Action | Detail |
|--------|--------|
| Print | Market price, bid, ask, option. |
| Order | `try_order("BUY", 1, ask)` |
| Print | Order line, risk status, position. |

**Tick 5 only:**

| Action | Detail |
|--------|--------|
| Order | `try_order("SELL", 1, bid)` |
| Print | SELL line, position, `realized_pnl` (status returned but not printed here). |

**After loop:**

| Line | Formula / meaning |
|------|-------------------|
| `avg_ms = sum(latencies) / len(latencies) / 1e6` | Mean ns → milliseconds (`1e6` ns per ms). |
| `backtest_pnl(prices)` | Separate strategy P/L on full list. |
| `count_trades()` | Rows in DB from approved sample orders. |

---

### `if __name__ == "__main__"` (lines 112–113)

Runs `main()` only when you execute `python3 main.py`, not when another file imports `main.py` (e.g. `distributed_demo.py` imports helpers without running the simulation).

---

## ⚡ `pricing.cpp` (every line explained)

| Line | Code | Meaning |
|------|------|---------|
| 1–2 | `#include <iomanip>`, `<iostream>` | Formatting and console I/O. |
| 4 | `int main(int argc, char* argv[])` | Standard C++ entry; args from command line. |
| 5 | `if (argc < 2) return 1` | Need spot price argument or exit with code 1. |
| 6 | `std::stod(argv[1])` | Parse first arg as double. |
| 7 | `bid = price - 0.05` | Bid side of book. |
| 8 | `ask = price + 0.05` | Ask side of book. |
| 9 | `option = price * 0.025` | Placeholder option value (2.5% of spot). |
| 10 | `cout` with `fixed`, `setprecision(2)` | Print 3 numbers, 2 decimals, space-separated + newline. |
| 11 | `return 0` | Success. |

**Contract with Python:** stdout must be exactly:  
`"<bid> <ask> <option>\n"`  
Example: `./pricing 100.14` → `100.09 100.19 2.50`

---

## 💾 `database.py` (every part explained)

### `DB` (line 4–5)

Path to **`trades.db`** in the same folder as `database.py`.

### `init_db()` (lines 7–11)

| SQL / step | Purpose |
|------------|---------|
| `DROP TABLE IF EXISTS trades` | Wipe old runs so each simulation starts clean. |
| `CREATE TABLE trades (side TEXT, qty INT, price REAL)` | Three columns only. |
| `commit()` | Save changes to disk. |

Uses `with sqlite3.connect(DB)` so the connection closes automatically.

### `save_trade(side, qty, price)` (lines 14–17)

| Part | Meaning |
|------|---------|
| `INSERT INTO trades VALUES (?, ?, ?)` | Parameterized insert (safe from SQL injection). |
| Tuple `(side, qty, price)` | One row per approved order in `try_order()`. |

### `count_trades()` (lines 20–22)

| Part | Meaning |
|------|---------|
| `SELECT COUNT(*) FROM trades` | Total rows. |
| `[0]` on `fetchone()` | Extract integer count for print at end of `main.py`. |

**Table shape after sample run:**

| side | qty | price |
|------|-----|-------|
| BUY | 1 | (ask at tick 0) |
| SELL | 1 | (bid at tick 5) |

---

## 📉 `backtest.py` (every part explained)

### `backtest_pnl(prices)` 

**Docstring:** Buy when price ≤ 99.5 (pay ask), sell when ≥ 100.5 (get bid), mark open shares to last price.

| Variable | Role |
|----------|------|
| `pos` | Share count in backtest (separate from `main.position`). |
| `cash` | Dollars after simulated buys/sells. |

**Loop for each `p` in `prices`:**

| Condition | Action |
|-----------|--------|
| `p <= 99.5` and `pos < 10` | Buy 1: `cash -= p + 0.05`, `pos += 1` |
| `p >= 100.5` and `pos > 0` | Sell 1: `cash += p - 0.05`, `pos -= 1` |
| Else | No trade this step |

**Return value:**

```
cash + pos * prices[-1]
```

= cash on hand + value of remaining shares at **last** price in the list.

**Does not** write to SQLite. **Does not** use `try_order()`. Can trade many times across 100 ticks if rules keep firing.

---

## 🌐 `distributed_demo.py` (every part explained)

### 📦 Imports

| Import | Use |
|--------|-----|
| `json` | Encode/decode price messages. |
| `socket` | TCP server and client. |
| `subprocess` | Spawn second Python process in `run_demo()`. |
| `sys` | `sys.executable`, `sys.argv` for roles. |
| `time` | Sleep between connect retries. |
| From `main` | Reuse `compile_pricing`, `gen_prices`, `get_quote`. |

### Constants

| Name | Value | Meaning |
|------|-------|---------|
| `HOST` | `127.0.0.1` | Localhost only. |
| `PORT` | `5555` | TCP port for price stream. |
| `TICKS` | `10` | Shorter stream than `main.py` (10 prices). |

---

### `market_node()` (lines 17–32)

| Step | What happens |
|------|----------------|
| `gen_prices(TICKS)` | Same generator as main, but only 10 prices. |
| `socket.AF_INET` | IPv4. |
| `SOCK_STREAM` | TCP (reliable, ordered bytes). |
| `SO_REUSEADDR` | Allows quick restart if port was recently used. |
| `bind` + `listen(1)` | Wait for one client. |
| `accept()` | Block until engine connects. |
| For each price | `json.dumps({"price": price}) + "\n"`, UTF-8 encode, `sendall`. |
| End | Send `{"done": true}\n` so client knows to stop. |

Prints log lines with `[market-node]` prefix.

---

### `engine_node()` (lines 35–71)

**Connect retry (lines 37–48):**

| Detail | Why |
|--------|-----|
| Up to 50 tries | Market process may start slightly later. |
| New socket each try | Avoid broken socket after refused connect. |
| `sleep(0.05)` | 50 ms between tries. |
| Failure | Raises `ConnectionRefusedError` with message. |

**Read loop (lines 52–71):**

| Part | Meaning |
|------|---------|
| `buf = ""` | Buffer for incomplete TCP chunks. |
| `recv(4096)` | Read up to 4 KB (may be partial line). |
| Split on `\n` | One JSON object per line (line protocol). |
| Skip empty lines | After strip. |
| `payload.get("done")` | Exit cleanly. |
| `float(payload["price"])` | Spot for this tick. |
| `get_quote(price)` | Same C++ path as `main.py`. |
| Print | Price, bid, ask (option discarded with `_`). |

---

### `run_demo()` (lines 74–83)

| Step | What happens |
|------|----------------|
| `Popen([sys.executable, __file__, "market"])` | Start **second Python process** as market server. |
| `engine_node()` | Current process acts as client/pricer. |
| `market.wait(timeout=10)` | Wait for server process to finish. |
| Non-zero exit | Propagate failure via `SystemExit`. |

---

### `if __name__ == "__main__"` (lines 86–93)

| `sys.argv[1]` | Behavior |
|---------------|----------|
| *(missing)* | `run_demo()` (both processes). |
| `"market"` | Only `market_node()`. |
| `"engine"` | Only `engine_node()`. |
| anything else | Same as missing → `run_demo()`. |

---

## 🙈 `.gitignore`

| Pattern | Ignores |
|---------|---------|
| `pricing` | Compiled C++ binary (machine-specific). |
| `trades.db` | Local SQLite data. |
| `__pycache__/` | Python bytecode cache folders. |
| `*.pyc` | Compiled Python files. |
| `.DS_Store` | macOS folder metadata. |

---

## ▶️ How to run

```bash
# Local pipeline (100 ticks, DB, backtest, latency)
python3 main.py

# Two processes over TCP (10 ticks, quotes only)
python3 distributed_demo.py

# Manual split:
python3 distributed_demo.py market   # terminal 1
python3 distributed_demo.py engine   # terminal 2

# Manual C++ build:
c++ -O2 pricing.cpp -o pricing
./pricing 100.00

# Inspect DB after main.py:
sqlite3 trades.db "SELECT * FROM trades;"
```

---

## 📺 Output (every printed line)

### `main.py`

| Output | Source |
|--------|--------|
| `Market Price: $...` | Tick 0 spot. |
| `Bid: ... \| Ask: ...` | C++ quote on tick 0. |
| `Option Value: ... (simplified)` | C++ placeholder option. |
| `Order: BUY 1 @ $...` | Tick 0, fill at ask. |
| `Risk Check: APPROVED` or would be `REJECTED` | Return value of `try_order`. |
| `Position: N share(s)` | Global `position` after buy. |
| `Order: SELL 1 @ $...` | Tick 5, fill at bid. |
| `Position: N shares` | After sell. |
| `Realized P&L: +X.XX` | Global `realized_pnl` after sell. |
| `Backtest P/L: ...` | `backtest_pnl(prices)`. |
| `Average Processing Latency: X.XX ms` | Mean of `latencies`. |
| `Trades Saved to SQLite: N` | `count_trades()`. |

### `distributed_demo.py`

| Prefix | Meaning |
|--------|---------|
| `[market-node] listening...` | Server ready. |
| `[market-node] engine connected...` | Client IP/port. |
| `[market-node] published price=...` | One JSON tick sent. |
| `[market-node] stream finished` | Done + done sentinel sent. |
| `[engine-node] connected...` | Client side up. |
| `[engine-node] recv price=... -> bid=... ask=...` | Priced tick. |
| `[engine-node] done` | Received `{"done": true}`. |
| `=== Distributed simulation...` | Banner when running combined mode. |

---

## 🧩 End-to-end picture

```
                    MAIN.PY
                    ───────
  gen_prices(100)
        │
        ▼
  feed_prices ──queue──▶ for each price:
        │                    get_quote → pricing.cpp
        │                    latencies[]
        │                    tick 0: BUY @ ask → DB
        │                    tick 5: SELL @ bid → DB
        ▼
  backtest_pnl(prices)     count_trades()
        │                        │
        └──────── print summary ─┘


              DISTRIBUTED_DEMO.PY
              ───────────────────
  Process A: market_node          Process B: engine_node
  gen_prices(10)                  connect + retry
  TCP send JSON lines      ───▶   get_quote per price
  {"done": true}                  print bid/ask
```

---

## ❓ FAQ

**Why are Backtest P/L and Realized P/L different?**  
They use **different rules**. Realized is from 2 manual orders on ticks 0 and 5. Backtest loops all 100 prices with 99.5 / 100.5 thresholds.

**Why `None` in the queue?**  
So the main thread knows the feed thread is done (sentinel pattern).

**Why daemon thread?**  
If main exits, Python will not hang waiting for the feeder.

**Does distributed mode use the database?**  
No. Only prints quotes unless you extend the code.

**What if C++ is missing?**  
`compile_pricing()` runs on startup; you need `c++` installed.

**What if port 5555 is busy?**  
Change `PORT` in `distributed_demo.py` or stop the other process using it.

---

## 🔧 Constants cheat sheet (all magic numbers)

| Value | Where | Meaning |
|-------|-------|---------|
| `42` | `gen_prices` | Random seed |
| `100` | `gen_prices()` default | Price count in main |
| `10` | `MAX_POS`, backtest | Max shares |
| `0.05` | C++, backtest | Half spread / slippage |
| `0.025` | C++ | Option placeholder ratio |
| `0.5` | `gen_prices` | Max random step per tick |
| `99.5` / `100.5` | `backtest.py` | Buy/s sell thresholds |
| `5555` | distributed | TCP port |
| `10` | `TICKS` | Prices in distributed mode |
| `50` × `0.05s` | engine connect | Max ~2.5s wait for server |
| `4096` | `recv` | Read buffer size |
| tick `0`, `5` | `main` | Sample order ticks |
