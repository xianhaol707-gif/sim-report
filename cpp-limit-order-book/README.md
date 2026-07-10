# C++ Limit Order Book + Matching Engine

A compact C++20 project for quant dev / HFT interview preparation. It implements a price-time priority limit order book, basic matching engine behavior, and microbenchmarks that are meant for relative comparisons on a local machine.

## Features

- Add, cancel, and modify orders
- Bid/ask book with best bid/ask queries
- Limit order matching
- Market order matching
- Trade generation
- Price-time priority inside each price level
- Ring buffer event queue example
- Simple memory pool component
- Latency histogram benchmark
- Python synthetic order generator
- CSV order-flow benchmark input
- CSV latency summary export

## Build

This project does not require CMake. On macOS with Xcode Command Line Tools:

```bash
make test
make demo
make bench
```

Run the demo:

```bash
./build/lob_demo
```

Run a benchmark with 100,000 synthetic events:

```bash
./build/lob_bench 100000
```

Generate synthetic CSV order flow:

```bash
python3 tools/generate_orders.py --count 100000 --output data/synthetic_orders.csv
```

Benchmark from that CSV and write latency metrics:

```bash
./build/lob_bench --input data/synthetic_orders.csv --latency-csv build/latency_summary.csv
```

## Design

The core book uses:

- `std::map<Price, std::list<Order>, std::greater<Price>>` for bids
- `std::map<Price, std::list<Order>>` for asks
- `std::unordered_map<OrderId, OrderLocation>` for O(1)-style cancel/modify lookup

Each price level stores orders in a FIFO list. Matching always consumes the front of the opposite best price level, so orders at the same price follow price-time priority.

## Tradeoffs

This is intentionally readable C++ rather than production HFT code.

- `std::map` gives clean price ordering but costs logarithmic lookup and pointer-heavy memory access.
- `std::list` gives stable iterators for cancel/modify but has poor cache locality.
- The ring buffer demonstrates event queue mechanics, but this benchmark is single-threaded.
- The memory pool is included as a reusable component; integrating it into book nodes would be a natural next optimization.
- Latency numbers on a MacBook Air are useful for relative comparison, not production latency claims.

## Example Output

```text
direct processing
  events=10000 trades=6989 live_orders=953
  throughput=7709107 events/sec
  latency count=10000 min=0ns p50=83ns p90=209ns p99=458ns max=4042ns
```

## Suggested Extensions

- Replace `std::map` with a tick-indexed price ladder for dense price ranges
- Integrate the memory pool into resting order allocation
- Add per-symbol books
- Add binary market data style event encoding
- Add a threaded producer/consumer benchmark
- Export latency histogram to CSV for plotting
