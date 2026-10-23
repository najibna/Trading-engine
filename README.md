# Trading Engine Prototype

Small **educational demo** of a market-making pipeline: simulated prices → C++ quotes → risk → orders → SQLite → backtest → latency stats. Optional **two-process TCP** demo for distributed-style feeds.

**Not production trading software.** No live exchanges, no real option models, no cluster deployment.

---

## Quick start

```bash
python3 main.py                 # full local simulation
python3 distributed_demo.py     # market-node + engine-node over TCP
```

Needs **Python 3** and **c++** on your PATH. First run compiles `pricing.cpp` → `./pricing`.

---

## How this maps to resume projects

| Resume line | What this repo demonstrates |
|-------------|----------------------------|
| **Real-Time Trading & Risk Platform** (Python, C++, SQL, distributed) | Python orchestration, C++ pricer subprocess, SQLite trade log, TCP market/engine nodes |
| Process market data | `gen_prices()` + threaded queue (local) or JSON over TCP (distributed) |
| Price options | C++ `pricing` binary returns bid/ask + simplified option value |
| Evaluate risk | `try_order()` rejects buys above 10 shares or sells with no position |
| Backtest strategies | `backtest_pnl()` replays the same price series with threshold rules |
| Benchmark latency | `perf_counter_ns()` around each C++ pricing call |
| **Low-Latency Market Making Engine** (Python, C++, Linux, multithreading) | Same stack; producer thread + main consumer; spread-based quotes; order simulation |
| Ingest market data | Queue feed thread or socket receiver |
| Compute prices | External C++ executable (typical split for hot path) |
| Manage risk | Position cap before fill |
| Execute orders | Simulated BUY @ ask / SELL @ bid + DB persist |
| Profile latency | Printed average ms per tick |

Runs on **macOS or Linux** (standard Python sockets and subprocess).

---

## System overview

```mermaid
flowchart LR
  MD[Market data] --> Q[Queue or TCP]
  Q --> PY[Python engine]
  PY --> CPP[C++ pricing]
  CPP --> PY
  PY --> RISK[Risk check]
  RISK --> ORD[Orders]
  ORD --> SQL[(SQLite)]
  PY --> BT[Backtest]
  PY --> LAT[Latency stats]
```

---

## Components

There are no heavy OOP layers—logic is grouped by **file/module**. Think of these as the roles:

```mermaid
classDiagram
  class MarketData {
    gen_prices()
    feed_prices()
  }
  class PricingEngine {
    pricing.cpp / pricing binary
    get_quote()
  }
  class RiskAndOrders {
    position, avg_cost
    try_order()
  }
  class TradeStore {
    init_db()
    save_trade()
    count_trades()
  }
  class BacktestEngine {
    backtest_pnl()
  }
  class DistributedNodes {
    market_node()
    engine_node()
  }

  MarketData --> PricingEngine : spot price
  PricingEngine --> RiskAndOrders : bid / ask
  RiskAndOrders --> TradeStore : fills
  MarketData --> BacktestEngine : historical prices
  DistributedNodes --> PricingEngine : remote ticks
```

| Module | Role |
|--------|------|
| **`main.py`** | End-to-end run: compile C++, DB init, price feed thread, quote loop, demo orders, latency + backtest summary |
| **`pricing.cpp`** | Hot path: `bid = spot − 0.05`, `ask = spot + 0.05`, placeholder option = `2.5% × spot` |
| **`database.py`** | SQLite `trades` table |
| **`backtest.py`** | Independent P&L replay on the same prices |
| **`distributed_demo.py`** | Separate processes: publisher vs consumer on `127.0.0.1:5555` |

**Shared state in `main.py` (intentionally minimal):** `position`, `avg_cost`, `realized_pnl`, `latencies`.

---

## Workflow 1 — Local market making (`main.py`)

```mermaid
sequenceDiagram
  participant T as Feed thread
  participant M as Main loop
  participant C as C++ pricing
  participant R as try_order
  participant D as SQLite

  T->>M: price tick (queue)
  M->>C: spot price
  C->>M: bid, ask, option
  Note over M: perf_counter_ns latency
  alt tick 0 or 5 (demo)
    M->>R: BUY @ ask or SELL @ bid
    R->>D: save_trade if approved
  end
  M->>M: backtest_pnl(all prices)
  M->>M: print avg latency + trade count
```

1. **Market data** — 100 random walks around $100 (`gen_prices`).
2. **Ingestion** — background thread pushes ticks into a `queue`; main thread consumes ( **multithreading** ).
3. **Pricing** — each tick calls `./pricing` via subprocess (**Python + C++**).
4. **Risk + execution** — demo BUY on first tick, SELL on sixth; max **10 shares** long.
5. **Storage** — approved fills → **`trades.db`** (**SQL**).
6. **Backtest** — same price list, simple buy-low / sell-high thresholds.
7. **Latency** — average time spent in step 3 per tick.

---

## Workflow 2 — Distributed-style feed (`distributed_demo.py`)

```mermaid
sequenceDiagram
  participant MN as market-node process
  participant TCP as TCP :5555
  participant EN as engine-node process
  participant C as C++ pricing

  MN->>TCP: listen
  EN->>TCP: connect
  loop 10 ticks
    MN->>TCP: {"price": ...}
    TCP->>EN: JSON line
    EN->>C: get_quote
    C->>EN: bid / ask
  end
  MN->>TCP: {"done": true}
```

Models a **remote market data service** and a **local pricing engine**—same idea as splitting feed handlers and strategy nodes, without Kubernetes or message brokers.

```bash
python3 distributed_demo.py          # one command
python3 distributed_demo.py market   # terminal A
python3 distributed_demo.py engine   # terminal B
```

---

## Example output (illustrative)

```
Market Price: $100.14
Bid: $100.09 | Ask: $100.19
Option Value: $2.50 (simplified)

Order: BUY 1 @ $100.19
Risk Check: APPROVED
Position: 1 share(s)

Backtest P&L: -9.18
Average Processing Latency: 7.45 ms
Trades Saved to SQLite: 2
```

Numbers change with the random seed and subprocess timing; shape of the output stays the same.

---

## Files

```
├── main.py              # Local pipeline + threading + latency
├── pricing.cpp          # C++ bid/ask/option
├── database.py          # SQLite
├── backtest.py          # Strategy replay
├── distributed_demo.py  # TCP two-process demo
└── README.md
```

Generated at runtime: `pricing` (binary), `trades.db`.

---

## Interview talking point

One sentence: *“Price ticks enter through a feed thread or TCP socket, get quoted in C++, pass a position limit, persist to SQLite, and we replay the series for backtest P&L while measuring per-tick pricing latency.”*

That is the story behind both resume bullets—implemented here at prototype scale.
