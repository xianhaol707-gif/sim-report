#pragma once

#include "lob/types.hpp"

#include <functional>
#include <list>
#include <map>
#include <optional>
#include <unordered_map>
#include <vector>

namespace lob {

class OrderBook {
public:
    struct RestingOrder {
        OrderId order_id{0};
        Side side{Side::Buy};
        Price price{0};
        Quantity quantity{0};
        TimestampNs timestamp_ns{0};
    };

    using TradeCallback = std::function<void(const Trade&)>;

    explicit OrderBook(TradeCallback on_trade = {});

    std::vector<Trade> add_limit(OrderId order_id, Side side, Price price, Quantity quantity);
    std::vector<Trade> add_market(OrderId order_id, Side side, Quantity quantity);
    bool cancel(OrderId order_id);
    bool modify(OrderId order_id, Price new_price, Quantity new_quantity);
    std::vector<Trade> process(const OrderRequest& request);

    [[nodiscard]] std::optional<Price> best_bid() const;
    [[nodiscard]] std::optional<Price> best_ask() const;
    [[nodiscard]] BestQuote best_quote() const;
    [[nodiscard]] Quantity quantity_at(Side side, Price price) const;
    [[nodiscard]] std::size_t live_order_count() const;
    [[nodiscard]] std::size_t price_level_count(Side side) const;

private:
    using OrderList = std::list<RestingOrder>;
    using Bids = std::map<Price, OrderList, std::greater<Price>>;
    using Asks = std::map<Price, OrderList>;

    struct OrderLocation {
        Side side{Side::Buy};
        Price price{0};
        OrderList::iterator iterator;
    };

    std::vector<Trade> match(
        OrderId taker_order_id,
        Side taker_side,
        Quantity& remaining,
        std::optional<Price> limit_price = std::nullopt);
    void rest(OrderId order_id, Side side, Price price, Quantity quantity);
    void erase_at(const OrderLocation& location);
    [[nodiscard]] bool crosses(Side taker_side, Price limit_price) const;

    Bids bids_;
    Asks asks_;
    std::unordered_map<OrderId, OrderLocation> order_index_;
    TradeCallback on_trade_;
    TimestampNs clock_{0};
};

}  // namespace lob
