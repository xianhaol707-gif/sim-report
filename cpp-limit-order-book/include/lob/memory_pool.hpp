#pragma once

#include <cstddef>
#include <memory>
#include <new>
#include <utility>
#include <vector>

namespace lob {

template <typename T, std::size_t BlockSize = 4096>
class MemoryPool {
public:
    MemoryPool() = default;
    MemoryPool(const MemoryPool&) = delete;
    MemoryPool& operator=(const MemoryPool&) = delete;

    template <typename... Args>
    T* create(Args&&... args) {
        if (free_list_ != nullptr) {
            Node* node = free_list_;
            free_list_ = free_list_->next;
            return new (&node->storage) T(std::forward<Args>(args)...);
        }

        if (blocks_.empty() || blocks_.back().used == BlockSize) {
            blocks_.push_back(Block{});
        }

        Block& block = blocks_.back();
        Node* node = &block.nodes[block.used++];
        return new (&node->storage) T(std::forward<Args>(args)...);
    }

    void destroy(T* object) {
        if (object == nullptr) {
            return;
        }
        object->~T();
        Node* node = reinterpret_cast<Node*>(object);
        node->next = free_list_;
        free_list_ = node;
    }

    [[nodiscard]] std::size_t block_count() const {
        return blocks_.size();
    }

private:
    union Node {
        alignas(T) unsigned char storage[sizeof(T)];
        Node* next;
    };

    struct Block {
        std::unique_ptr<Node[]> nodes{std::make_unique<Node[]>(BlockSize)};
        std::size_t used{0};
    };

    std::vector<Block> blocks_;
    Node* free_list_{nullptr};
};

}  // namespace lob
