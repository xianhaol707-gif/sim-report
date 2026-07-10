CXX ?= clang++
CXXFLAGS ?= -std=c++20 -O3 -Wall -Wextra -Wpedantic -Iinclude
DEBUG_FLAGS ?= -std=c++20 -O0 -g -Wall -Wextra -Wpedantic -Iinclude

BUILD_DIR := build
LIB_SRCS := src/order_book.cpp src/types.cpp src/latency_histogram.cpp
DEMO_SRCS := src/main.cpp $(LIB_SRCS)
BENCH_SRCS := src/benchmark.cpp $(LIB_SRCS)
TEST_SRCS := tests/order_book_tests.cpp $(LIB_SRCS)

.PHONY: all demo bench test debug clean

all: demo bench

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

demo: $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(DEMO_SRCS) -o $(BUILD_DIR)/lob_demo

bench: $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(BENCH_SRCS) -o $(BUILD_DIR)/lob_bench

test: $(BUILD_DIR)
	$(CXX) $(DEBUG_FLAGS) $(TEST_SRCS) -o $(BUILD_DIR)/order_book_tests
	./$(BUILD_DIR)/order_book_tests

debug: $(BUILD_DIR)
	$(CXX) $(DEBUG_FLAGS) $(DEMO_SRCS) -o $(BUILD_DIR)/lob_demo_debug

clean:
	rm -rf $(BUILD_DIR)
