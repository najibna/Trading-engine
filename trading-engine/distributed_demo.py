#!/usr/bin/env python3
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
        conn, _ = srv.accept()
        with conn:
            for price in prices:
                conn.sendall((json.dumps({"price": price}) + "\n").encode())
            conn.sendall(b'{"done": true}\n')


def engine_node():
    time.sleep(0.3)
    compile_pricing()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        buf = ""
        while True:
            chunk = sock.recv(4096).decode()
            if not chunk:
                break
            buf += chunk
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                payload = json.loads(line)
                if payload.get("done"):
                    return
                price = float(payload["price"])
                bid, ask, _ = get_quote(price)
                print(f"price={price:.2f} bid={bid:.2f} ask={ask:.2f}")


def run_demo():
    market = subprocess.Popen([sys.executable, __file__, "market"])
    try:
        engine_node()
    finally:
        market.wait(timeout=10)


if __name__ == "__main__":
    role = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if role == "market":
        market_node()
    elif role == "engine":
        engine_node()
    else:
        run_demo()
