#pragma once

#include <algorithm>
#include <cstdint>
#include <iomanip>
#include <iosfwd>
#include <vector>

namespace lob {

class LatencyHistogram {
public:
    void record(std::uint64_t latency_ns) {
        samples_.push_back(latency_ns);
    }

    [[nodiscard]] std::size_t size() const {
        return samples_.size();
    }

    [[nodiscard]] std::uint64_t percentile(double pct) {
        if (samples_.empty()) {
            return 0;
        }
        sort_once();
        const double clamped = std::clamp(pct, 0.0, 100.0);
        const auto index = static_cast<std::size_t>((clamped / 100.0) * (samples_.size() - 1));
        return samples_[index];
    }

    [[nodiscard]] std::uint64_t min() {
        return percentile(0.0);
    }

    [[nodiscard]] std::uint64_t max() {
        return percentile(100.0);
    }

private:
    void sort_once() {
        if (!sorted_) {
            std::sort(samples_.begin(), samples_.end());
            sorted_ = true;
        }
    }

    std::vector<std::uint64_t> samples_;
    bool sorted_{false};
};

std::ostream& operator<<(std::ostream& os, LatencyHistogram& hist);

}  // namespace lob
