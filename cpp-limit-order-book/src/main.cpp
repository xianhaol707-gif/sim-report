#include "lob/order_book.hpp"

#include <iostream>

int main() {
    lob::OrderBook book;

    book.add_limit(1, lob::Side::Buy, 10000, 100);
    book.add_limit(2, lob::Side::Buy, 10001, 50);
    book.add_limit(3, lob::Side::Sell, 10005, 80);

    std::cout << "Initial quote: bid=" << *book.best_bid() << " ask=" << *book.best_ask() << '\n';

    const auto trades = book.add_limit(4, lob::Side::Buy, 10005, 120);
    for (const auto& trade : trades) {
        std::cout << trade << '\n';
    }

    const auto quote = book.best_quote();
    std::cout << "After crossing order: ";
    if (quote.has_bid) {
        std::cout << "bid=" << quote.bid_price << "x" << quote.bid_quantity << " ";
    }
    if (quote.has_ask) {
        std::cout << "ask=" << quote.ask_price << "x" << quote.ask_quantity;
    }
    std::cout << '\n';

    return 0;
}
