#include "lob/order_book.hpp"
#include "lob/ring_buffer.hpp"

#include <cstdlib>
#include <iostream>
#include <string_view>

namespace {

void require(bool condition, std::string_view message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        std::exit(1);
    }
}

void test_limit_matching_and_best_quote() {
    lob::OrderBook book;
    book.add_limit(1, lob::Side::Sell, 101, 10);
    book.add_limit(2, lob::Side::Sell, 102, 20);

    const auto trades = book.add_limit(3, lob::Side::Buy, 101, 15);
    require(trades.size() == 1, "buy limit should only trade marketable price levels");
    require(trades[0].maker_order_id == 1, "trade should hit oldest ask at best price");
    require(trades[0].price == 101, "trade price should be maker price");
    require(trades[0].quantity == 10, "trade quantity should consume available ask");
    require(book.quantity_at(lob::Side::Buy, 101) == 5, "unfilled buy limit should rest");
    require(book.best_ask() == 102, "non-marketable ask should remain best ask");
}

void test_price_time_priority() {
    lob::OrderBook book;
    book.add_limit(1, lob::Side::Sell, 100, 10);
    book.add_limit(2, lob::Side::Sell, 100, 10);

    const auto trades = book.add_market(3, lob::Side::Buy, 15);
    require(trades.size() == 2, "market order should sweep FIFO queue");
    require(trades[0].maker_order_id == 1, "first maker should be oldest order");
    require(trades[1].maker_order_id == 2, "second maker should be next oldest order");
    require(trades[1].quantity == 5, "second maker should be partially filled");
    require(book.quantity_at(lob::Side::Sell, 100) == 5, "remaining maker quantity should stay in book");
}

void test_cancel_and_modify() {
    lob::OrderBook book;
    book.add_limit(1, lob::Side::Buy, 99, 10);
    book.add_limit(2, lob::Side::Buy, 98, 20);

    require(book.cancel(1), "cancel should find live order");
    require(!book.cancel(1), "second cancel should miss");
    require(book.best_bid() == 98, "cancel should remove best bid");

    require(book.modify(2, 100, 15), "modify should replace resting order");
    require(book.best_bid() == 100, "modify should update price");
    require(book.quantity_at(lob::Side::Buy, 100) == 15, "modify should update quantity");
}

void test_modify_can_cross() {
    lob::OrderBook book;
    book.add_limit(1, lob::Side::Sell, 105, 10);
    book.add_limit(2, lob::Side::Buy, 100, 10);

    require(book.modify(2, 106, 6), "modify should accept a marketable replacement");
    require(book.live_order_count() == 1, "fully filled modified order should not rest");
    require(book.quantity_at(lob::Side::Sell, 105) == 4, "modified order should trade against opposite book");
}

void test_ring_buffer() {
    lob::RingBuffer<int, 4> queue;
    require(queue.push(1), "push 1");
    require(queue.push(2), "push 2");
    require(queue.push(3), "push 3");
    require(!queue.push(4), "one slot remains empty to distinguish full from empty");
    require(queue.pop() == 1, "pop 1");
    require(queue.pop() == 2, "pop 2");
    require(queue.pop() == 3, "pop 3");
    require(!queue.pop().has_value(), "empty pop");
}

}  // namespace

int main() {
    test_limit_matching_and_best_quote();
    test_price_time_priority();
    test_cancel_and_modify();
    test_modify_can_cross();
    test_ring_buffer();
    std::cout << "all tests passed\n";
    return 0;
}
