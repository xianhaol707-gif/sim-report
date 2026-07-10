#include "lob/order_book.hpp"

#include <algorithm>
#include <stdexcept>

namespace lob {

OrderBook::OrderBook(TradeCallback on_trade) : on_trade_(std::move(on_trade)) {}

std::vector<Trade> OrderBook::add_limit(OrderId order_id, Side side, Price price, Quantity quantity) {
    if (order_id == 0 || price <= 0 || quantity == 0 || order_index_.contains(order_id)) {
        return {};
    }

    Quantity remaining = quantity;
    std::vector<Trade> trades;
    if (crosses(side, price)) {
        trades = match(order_id, side, remaining, price);
    }

    if (remaining > 0) {
        rest(order_id, side, price, remaining);
    }
    return trades;
}

std::vector<Trade> OrderBook::add_market(OrderId order_id, Side side, Quantity quantity) {
    if (order_id == 0 || quantity == 0) {
        return {};
    }
    Quantity remaining = quantity;
    return match(order_id, side, remaining);
}

bool OrderBook::cancel(OrderId order_id) {
    auto found = order_index_.find(order_id);
    if (found == order_index_.end()) {
        return false;
    }
    erase_at(found->second);
    order_index_.erase(found);
    return true;
}

bool OrderBook::modify(OrderId order_id, Price new_price, Quantity new_quantity) {
    auto found = order_index_.find(order_id);
    if (found == order_index_.end() || new_price <= 0) {
        return false;
    }

    const Side side = found->second.side;
    cancel(order_id);

    if (new_quantity == 0) {
        return true;
    }

    add_limit(order_id, side, new_price, new_quantity);
    return true;
}

std::vector<Trade> OrderBook::process(const OrderRequest& request) {
    switch (request.event_type) {
        case EventType::Add:
            return add_limit(request.order_id, request.side, request.price, request.quantity);
        case EventType::Market:
            return add_market(request.order_id, request.side, request.quantity);
        case EventType::Cancel:
            cancel(request.order_id);
            return {};
        case EventType::Modify:
            modify(request.order_id, request.price, request.quantity);
            return {};
    }
    return {};
}

std::optional<Price> OrderBook::best_bid() const {
    if (bids_.empty()) {
        return std::nullopt;
    }
    return bids_.begin()->first;
}

std::optional<Price> OrderBook::best_ask() const {
    if (asks_.empty()) {
        return std::nullopt;
    }
    return asks_.begin()->first;
}

BestQuote OrderBook::best_quote() const {
    BestQuote quote;
    if (!bids_.empty()) {
        quote.has_bid = true;
        quote.bid_price = bids_.begin()->first;
        for (const auto& order : bids_.begin()->second) {
            quote.bid_quantity += order.quantity;
        }
    }
    if (!asks_.empty()) {
        quote.has_ask = true;
        quote.ask_price = asks_.begin()->first;
        for (const auto& order : asks_.begin()->second) {
            quote.ask_quantity += order.quantity;
        }
    }
    return quote;
}

Quantity OrderBook::quantity_at(Side side, Price price) const {
    Quantity quantity = 0;
    if (side == Side::Buy) {
        auto level = bids_.find(price);
        if (level == bids_.end()) {
            return 0;
        }
        for (const auto& order : level->second) {
            quantity += order.quantity;
        }
        return quantity;
    }

    auto level = asks_.find(price);
    if (level == asks_.end()) {
        return 0;
    }
    for (const auto& order : level->second) {
        quantity += order.quantity;
    }
    return quantity;
}

std::size_t OrderBook::live_order_count() const {
    return order_index_.size();
}

std::size_t OrderBook::price_level_count(Side side) const {
    return side == Side::Buy ? bids_.size() : asks_.size();
}

std::vector<Trade> OrderBook::match(
    OrderId taker_order_id,
    Side taker_side,
    Quantity& remaining,
    std::optional<Price> limit_price) {
    std::vector<Trade> trades;

    auto match_one_side = [&](auto& opposite_book) {
        while (remaining > 0 && !opposite_book.empty()) {
            auto level = opposite_book.begin();
            if (limit_price.has_value()) {
                const bool can_trade = taker_side == Side::Buy ? *limit_price >= level->first
                                                               : *limit_price <= level->first;
                if (!can_trade) {
                    break;
                }
            }
            auto& queue = level->second;

            while (remaining > 0 && !queue.empty()) {
                auto maker = queue.begin();
                const Quantity traded = std::min(remaining, maker->quantity);
                Trade trade{taker_order_id, maker->order_id, taker_side, maker->price, traded};
                trades.push_back(trade);
                if (on_trade_) {
                    on_trade_(trade);
                }

                remaining -= traded;
                maker->quantity -= traded;

                if (maker->quantity == 0) {
                    order_index_.erase(maker->order_id);
                    queue.erase(maker);
                }
            }

            if (queue.empty()) {
                opposite_book.erase(level);
            }
        }
    };

    if (taker_side == Side::Buy) {
        match_one_side(asks_);
    } else {
        match_one_side(bids_);
    }

    return trades;
}

void OrderBook::rest(OrderId order_id, Side side, Price price, Quantity quantity) {
    RestingOrder order{order_id, side, price, quantity, ++clock_};

    if (side == Side::Buy) {
        auto& queue = bids_[price];
        queue.push_back(order);
        auto it = std::prev(queue.end());
        order_index_[order_id] = OrderLocation{side, price, it};
        return;
    }

    auto& queue = asks_[price];
    queue.push_back(order);
    auto it = std::prev(queue.end());
    order_index_[order_id] = OrderLocation{side, price, it};
}

void OrderBook::erase_at(const OrderLocation& location) {
    if (location.side == Side::Buy) {
        auto level = bids_.find(location.price);
        if (level == bids_.end()) {
            return;
        }
        level->second.erase(location.iterator);
        if (level->second.empty()) {
            bids_.erase(level);
        }
        return;
    }

    auto level = asks_.find(location.price);
    if (level == asks_.end()) {
        return;
    }
    level->second.erase(location.iterator);
    if (level->second.empty()) {
        asks_.erase(level);
    }
}

bool OrderBook::crosses(Side taker_side, Price limit_price) const {
    if (taker_side == Side::Buy) {
        return !asks_.empty() && limit_price >= asks_.begin()->first;
    }
    return !bids_.empty() && limit_price <= bids_.begin()->first;
}

}  // namespace lob
