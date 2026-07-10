#!/usr/bin/env python3
"""Generate synthetic order flow for experimenting with the matching engine."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


def generate(count: int, seed: int, mid_price: int) -> list[dict[str, object]]:
    rng = random.Random(seed)
    live_ids: list[int] = []
    next_id = 1
    rows: list[dict[str, object]] = []

    for _ in range(count):
        roll = rng.randrange(100)

        if roll < 10 and live_ids:
            idx = rng.randrange(len(live_ids))
            order_id = live_ids.pop(idx)
            rows.append(
                {
                    "event": "CANCEL",
                    "order_id": order_id,
                    "side": "",
                    "type": "",
                    "price": "",
                    "quantity": "",
                }
            )
            continue

        if roll < 18 and live_ids:
            order_id = rng.choice(live_ids)
            side = rng.choice(["BUY", "SELL"])
            rows.append(
                {
                    "event": "MODIFY",
                    "order_id": order_id,
                    "side": side,
                    "type": "LIMIT",
                    "price": mid_price + rng.randint(-50, 50),
                    "quantity": rng.randint(1, 500),
                }
            )
            continue

        side = rng.choice(["BUY", "SELL"])
        quantity = rng.randint(1, 500)

        if roll < 25:
            rows.append(
                {
                    "event": "MARKET",
                    "order_id": next_id,
                    "side": side,
                    "type": "MARKET",
                    "price": "",
                    "quantity": quantity,
                }
            )
            next_id += 1
            continue

        rows.append(
            {
                "event": "ADD",
                "order_id": next_id,
                "side": side,
                "type": "LIMIT",
                "price": mid_price + rng.randint(-50, 50),
                "quantity": quantity,
            }
        )
        live_ids.append(next_id)
        next_id += 1

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--mid-price", type=int, default=10_000)
    parser.add_argument("--output", type=Path, default=Path("data/synthetic_orders.csv"))
    args = parser.parse_args()

    rows = generate(args.count, args.seed, args.mid_price)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["event", "order_id", "side", "type", "price", "quantity"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
