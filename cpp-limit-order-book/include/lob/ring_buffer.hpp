#pragma once

#include <array>
#include <cstddef>
#include <optional>

namespace lob {

template <typename T, std::size_t Capacity>
class RingBuffer {
public:
    static_assert(Capacity > 1, "RingBuffer capacity must be greater than 1");

    [[nodiscard]] bool push(const T& value) {
        const auto next = increment(head_);
        if (next == tail_) {
            return false;
        }
        data_[head_] = value;
        head_ = next;
        return true;
    }

    [[nodiscard]] std::optional<T> pop() {
        if (tail_ == head_) {
            return std::nullopt;
        }
        T value = data_[tail_];
        tail_ = increment(tail_);
        return value;
    }

    [[nodiscard]] bool empty() const {
        return head_ == tail_;
    }

    [[nodiscard]] std::size_t size() const {
        if (head_ >= tail_) {
            return head_ - tail_;
        }
        return Capacity - tail_ + head_;
    }

    [[nodiscard]] constexpr std::size_t capacity() const {
        return Capacity - 1;
    }

private:
    [[nodiscard]] constexpr std::size_t increment(std::size_t index) const {
        return (index + 1) % Capacity;
    }

    std::array<T, Capacity> data_{};
    std::size_t head_{0};
    std::size_t tail_{0};
};

}  // namespace lob
