#include "lob/latency_histogram.hpp"

#include <ostream>

namespace lob {

std::ostream& operator<<(std::ostream& os, LatencyHistogram& hist) {
    os << "count=" << hist.size() << " min=" << hist.min() << "ns"
       << " p50=" << hist.percentile(50.0) << "ns"
       << " p90=" << hist.percentile(90.0) << "ns"
       << " p99=" << hist.percentile(99.0) << "ns"
       << " max=" << hist.max() << "ns";
    return os;
}

}  // namespace lob
