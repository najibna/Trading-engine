#!/usr/bin/env python3
"""Two-process demo: market-node publishes ticks over TCP, engine-node prices them."""

import json
import socket
import subprocess
import sys
import time

from main import compile_pricing, gen_prices, get_quote

HOST = "127.0.0.1"
PORT = 5555
TICKS = 10


def market_node():
    prices = gen_prices(TICKS)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(1)
        print(f"[market-node] listening on {HOST}:{PORT}")
        conn, addr = srv.accept()
        with conn:
            print(f"[market-node] engine connected from {addr[0]}:{addr[1]}")
            for price in prices:
                msg = json.dumps({"price": price}) + "\n"
                conn.sendall(msg.encode())
                print(f"[market-node] published price={price:.2f}")
            conn.sendall(b'{"done": true}\n')
            print("[market-node] stream finished")


def engine_node():
    compile_pricing()
    sock = None
    for _ in range(50):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((HOST, PORT))
            break
        except ConnectionRefusedError:
            sock.close()
            sock = None
            time.sleep(0.05)
    if sock is None:
        raise ConnectionRefusedError(f"could not connect to {HOST}:{PORT}")

    with sock:
        print(f"[engine-node] connected to {HOST}:{PORT}")
        buf = ""
        while True:
            chunk = sock.recv(4096).decode()
            if not chunk:
                break
            buf += chunk
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                if not line.strip():
                    continue
                payload = json.loads(line)
                if payload.get("done"):
                    print("[engine-node] done")
                    return
                price = float(payload["price"])
                bid, ask, _ = get_quote(price)
                print(
                    f"[engine-node] recv price={price:.2f} -> "
                    f"bid={bid:.2f} ask={ask:.2f}"
                )


def run_demo():
    print("=== Distributed simulation (2 processes, TCP) ===\n")
    market = subprocess.Popen([sys.executable, __file__, "market"])
    try:
        engine_node()
    finally:
        market.wait(timeout=10)
        if market.returncode not in (0, None):
            raise SystemExit(market.returncode)
    print()


if __name__ == "__main__":
    role = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if role == "market":
        market_node()
    elif role == "engine":
        engine_node()
    else:
        run_demo()
