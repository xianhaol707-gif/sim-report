#include "lob/types.hpp"

#include <ostream>

namespace lob {

std::string_view to_string(Side side) {
    return side == Side::Buy ? "BUY" : "SELL";
}

std::string_view to_string(EventType type) {
    switch (type) {
        case EventType::Add:
            return "ADD";
        case EventType::Cancel:
            return "CANCEL";
        case EventType::Modify:
            return "MODIFY";
        case EventType::Market:
            return "MARKET";
    }
    return "UNKNOWN";
}

std::ostream& operator<<(std::ostream& os, const Trade& trade) {
    os << "trade taker=" << trade.taker_order_id << " maker=" << trade.maker_order_id
       << " side=" << to_string(trade.taker_side) << " price=" << trade.price
       << " qty=" << trade.quantity;
    return os;
}

}  // namespace lob
