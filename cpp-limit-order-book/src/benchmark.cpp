#include "lob/latency_histogram.hpp"
#include "lob/memory_pool.hpp"
#include "lob/order_book.hpp"
#include "lob/ring_buffer.hpp"

#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;

struct BenchmarkOptions {
    std::size_t count{100000};
    std::string input_path;
    std::string latency_csv_path;
};

struct BenchmarkResult {
    std::size_t events{0};
    std::uint64_t trades{0};
    std::size_t live_orders{0};
    double seconds{0.0};
    lob::LatencyHistogram latency;
};

std::vector<std::string> split_csv_line(const std::string& line) {
    std::vector<std::string> fields;
    std::string field;
    std::istringstream stream(line);
    while (std::getline(stream, field, ',')) {
        fields.push_back(field);
    }
    if (!line.empty() && line.back() == ',') {
        fields.emplace_back();
    }
    return fields;
}

std::string trim(std::string value) {
    while (!value.empty() && (value.back() == '\r' || value.back() == '\n' || value.back() == ' ')) {
        value.pop_back();
    }
    std::size_t start = 0;
    while (start < value.size() && value[start] == ' ') {
        ++start;
    }
    return value.substr(start);
}

lob::Side parse_side(std::string_view value) {
    return value == "SELL" ? lob::Side::Sell : lob::Side::Buy;
}

lob::EventType parse_event(std::string_view value) {
    if (value == "CANCEL") {
        return lob::EventType::Cancel;
    }
    if (value == "MODIFY") {
        return lob::EventType::Modify;
    }
    if (value == "MARKET") {
        return lob::EventType::Market;
    }
    return lob::EventType::Add;
}

std::vector<lob::OrderRequest> load_orders_csv(const std::string& path) {
    std::ifstream file(path);
    if (!file) {
        throw std::runtime_error("could not open input CSV: " + path);
    }

    std::vector<lob::OrderRequest> requests;
    std::string line;
    std::getline(file, line);  // header

    while (std::getline(file, line)) {
        if (line.empty()) {
            continue;
        }
        auto fields = split_csv_line(line);
        if (fields.size() < 6) {
            fields.resize(6);
        }
        for (auto& field : fields) {
            field = trim(field);
        }
        lob::OrderRequest request;
        request.event_type = parse_event(fields[0]);
        request.order_id = static_cast<lob::OrderId>(std::stoull(fields[1]));
        request.side = fields[2].empty() ? lob::Side::Buy : parse_side(fields[2]);
        request.order_type = fields[3] == "MARKET" ? lob::OrderType::Market : lob::OrderType::Limit;
        request.price = fields[4].empty() ? 0 : static_cast<lob::Price>(std::stoll(fields[4]));
        request.quantity = fields[5].empty() ? 0 : static_cast<lob::Quantity>(std::stoul(fields[5]));
        requests.push_back(request);
    }

    return requests;
}

std::vector<lob::OrderRequest> make_synthetic_orders(std::size_t count) {
    std::mt19937_64 rng(42);
    std::uniform_int_distribution<int> side_dist(0, 1);
    std::uniform_int_distribution<int> event_dist(0, 99);
    std::uniform_int_distribution<int> price_offset(-50, 50);
    std::uniform_int_distribution<int> qty_dist(1, 500);

    std::vector<lob::OrderRequest> requests;
    requests.reserve(count);
    std::vector<lob::OrderId> live_ids;
    live_ids.reserve(count);

    lob::OrderId next_id = 1;
    constexpr lob::Price mid = 10000;

    for (std::size_t i = 0; i < count; ++i) {
        const int event_roll = event_dist(rng);
        if (event_roll < 10 && !live_ids.empty()) {
            const auto index = static_cast<std::size_t>(rng() % live_ids.size());
            requests.push_back({lob::EventType::Cancel, live_ids[index]});
            live_ids[index] = live_ids.back();
            live_ids.pop_back();
            continue;
        }

        if (event_roll < 18 && !live_ids.empty()) {
            const auto index = static_cast<std::size_t>(rng() % live_ids.size());
            const auto side = side_dist(rng) == 0 ? lob::Side::Buy : lob::Side::Sell;
            const lob::Price price = mid + price_offset(rng);
            const lob::Quantity qty = static_cast<lob::Quantity>(qty_dist(rng));
            requests.push_back({lob::EventType::Modify, live_ids[index], side, lob::OrderType::Limit, price, qty});
            continue;
        }

        const auto side = side_dist(rng) == 0 ? lob::Side::Buy : lob::Side::Sell;
        const lob::Quantity qty = static_cast<lob::Quantity>(qty_dist(rng));
        if (event_roll < 25) {
            requests.push_back({lob::EventType::Market, next_id++, side, lob::OrderType::Market, 0, qty});
            continue;
        }

        const lob::Price price = mid + price_offset(rng);
        requests.push_back({lob::EventType::Add, next_id, side, lob::OrderType::Limit, price, qty});
        live_ids.push_back(next_id);
        ++next_id;
    }

    return requests;
}

BenchmarkResult run_direct_benchmark(const std::vector<lob::OrderRequest>& requests) {
    lob::OrderBook book;
    BenchmarkResult result;
    result.events = requests.size();

    const auto batch_start = Clock::now();
    for (const auto& request : requests) {
        const auto start = Clock::now();
        const auto trades = book.process(request);
        const auto end = Clock::now();
        result.trades += trades.size();
        result.latency.record(
            static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count()));
    }
    const auto batch_end = Clock::now();

    result.seconds = std::chrono::duration<double>(batch_end - batch_start).count();
    result.live_orders = book.live_order_count();

    std::cout << "direct processing\n";
    std::cout << "  events=" << result.events << " trades=" << result.trades
              << " live_orders=" << result.live_orders << '\n';
    std::cout << "  throughput=" << static_cast<std::uint64_t>(result.events / result.seconds) << " events/sec\n";
    std::cout << "  latency " << result.latency << "\n\n";

    return result;
}

void run_ring_buffer_benchmark(const std::vector<lob::OrderRequest>& requests) {
    lob::RingBuffer<lob::OrderRequest, 1 << 16> queue;
    lob::OrderBook book;
    std::size_t processed = 0;

    const auto start = Clock::now();
    for (const auto& request : requests) {
        if (!queue.push(request)) {
            while (auto next = queue.pop()) {
                book.process(*next);
                ++processed;
            }
            const bool accepted = queue.push(request);
            if (!accepted) {
                std::cerr << "ring buffer unexpectedly full after drain\n";
                return;
            }
        }
    }
    while (auto next = queue.pop()) {
        book.process(*next);
        ++processed;
    }
    const auto end = Clock::now();

    const double seconds = std::chrono::duration<double>(end - start).count();
    std::cout << "ring buffer event queue\n";
    std::cout << "  events=" << processed << " live_orders=" << book.live_order_count() << '\n';
    std::cout << "  throughput=" << static_cast<std::uint64_t>(processed / seconds) << " events/sec\n\n";
}

void run_memory_pool_smoke() {
    struct Node {
        std::uint64_t id;
        std::uint64_t value;
    };

    lob::MemoryPool<Node> pool;
    std::vector<Node*> nodes;
    nodes.reserve(10000);
    for (std::uint64_t i = 0; i < 10000; ++i) {
        nodes.push_back(pool.create(i, i * 2));
    }
    for (auto* node : nodes) {
        pool.destroy(node);
    }
    std::cout << "memory pool smoke\n";
    std::cout << "  allocated_blocks=" << pool.block_count() << " reusable_nodes=" << nodes.size() << "\n\n";
}

void write_latency_csv(const std::string& path, BenchmarkResult& result) {
    const auto parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }

    std::ofstream file(path);
    if (!file) {
        throw std::runtime_error("could not write latency CSV: " + path);
    }

    file << "metric,value\n";
    file << "events," << result.events << '\n';
    file << "trades," << result.trades << '\n';
    file << "live_orders," << result.live_orders << '\n';
    file << "seconds," << result.seconds << '\n';
    file << "throughput_events_per_sec," << static_cast<std::uint64_t>(result.events / result.seconds) << '\n';
    file << "latency_min_ns," << result.latency.min() << '\n';
    file << "latency_p50_ns," << result.latency.percentile(50.0) << '\n';
    file << "latency_p90_ns," << result.latency.percentile(90.0) << '\n';
    file << "latency_p99_ns," << result.latency.percentile(99.0) << '\n';
    file << "latency_max_ns," << result.latency.max() << '\n';
}

BenchmarkOptions parse_args(int argc, char** argv) {
    BenchmarkOptions options;

    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--input" && i + 1 < argc) {
            options.input_path = argv[++i];
        } else if (arg == "--latency-csv" && i + 1 < argc) {
            options.latency_csv_path = argv[++i];
        } else if (arg == "--count" && i + 1 < argc) {
            options.count = static_cast<std::size_t>(std::stoull(argv[++i]));
        } else if (!arg.empty() && arg[0] != '-') {
            options.count = static_cast<std::size_t>(std::stoull(arg));
        } else {
            throw std::runtime_error(
                "usage: lob_bench [count] [--count n] [--input orders.csv] [--latency-csv output.csv]");
        }
    }

    return options;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const auto options = parse_args(argc, argv);
        const auto requests = options.input_path.empty() ? make_synthetic_orders(options.count)
                                                         : load_orders_csv(options.input_path);
        auto result = run_direct_benchmark(requests);
        run_ring_buffer_benchmark(requests);
        run_memory_pool_smoke();

        if (!options.latency_csv_path.empty()) {
            write_latency_csv(options.latency_csv_path, result);
            std::cout << "wrote latency summary to " << options.latency_csv_path << '\n';
        }
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
