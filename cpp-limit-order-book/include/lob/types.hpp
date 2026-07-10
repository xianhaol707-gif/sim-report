#pragma once

#include <cstdint>
#include <iosfwd>
#include <string_view>

namespace lob {

using OrderId = std::uint64_t;
using Price = std::int64_t;
using Quantity = std::uint32_t;
using TimestampNs = std::uint64_t;

enum class Side : std::uint8_t {
    Buy,
    Sell,
};

enum class OrderType : std::uint8_t {
    Limit,
    Market,
};

enum class EventType : std::uint8_t {
    Add,
    Cancel,
    Modify,
    Market,
};

struct OrderRequest {
    EventType event_type{EventType::Add};
    OrderId order_id{0};
    Side side{Side::Buy};
    OrderType order_type{OrderType::Limit};
    Price price{0};
    Quantity quantity{0};
};

struct Trade {
    OrderId taker_order_id{0};
    OrderId maker_order_id{0};
    Side taker_side{Side::Buy};
    Price price{0};
    Quantity quantity{0};
};

struct BestQuote {
    bool has_bid{false};
    Price bid_price{0};
    Quantity bid_quantity{0};
    bool has_ask{false};
    Price ask_price{0};
    Quantity ask_quantity{0};
};

std::string_view to_string(Side side);
std::string_view to_string(EventType type);
std::ostream& operator<<(std::ostream& os, const Trade& trade);

}  // namespace lob
