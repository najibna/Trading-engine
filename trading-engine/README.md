# Trading Engine Prototype

Simulated prices → C++ quotes → risk → SQLite → backtest.

## Quick start

```bash
cd trading-engine
python3 main.py
python3 distributed_demo.py
```

## Architecture

Market data (thread or TCP) → Python → C++ pricing → risk → orders → SQLite.
