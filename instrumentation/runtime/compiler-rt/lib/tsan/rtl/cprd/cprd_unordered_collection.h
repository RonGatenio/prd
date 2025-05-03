#ifndef CPRD_UNORDERED_COLLECTION_H
#define CPRD_UNORDERED_COLLECTION_H

#include "cprd_common.h"

namespace cprd {

/*  fixed sized UnorderedCollection class
    not thread safe!
*/
template <typename T, u32 MaxSize>
class UnorderedCollection {
private:
  struct Item {
    bool m_valid;
    T m_data;
  };

public:
  class Iterator {
    friend class UnorderedCollection;

  protected:
    UnorderedCollection& m_collection;
    u32 m_index;

    void find_valid() {
      for (; m_index < MaxSize; m_index++) {
        if (m_collection.m_items[m_index].m_valid) {
          break;
        }
      }
    }

  public:
    Iterator(UnorderedCollection& collection, u32 index) : m_collection(collection), m_index(index) {
      find_valid();
    }

    Iterator& operator++() {
      m_index++;
      find_valid();
      return *this;
    }

    T& operator*() {
      return m_collection.m_items[m_index].m_data;
    }

    T* operator->() {
      return &m_collection.m_items[m_index].m_data;
    }

    bool operator==(const Iterator& other) const {
      return m_index == other.m_index;
    }

    bool operator!=(const Iterator& other) const {
      return !(*this == other);
    }
  };

private:
  Item m_items[MaxSize];
  u32 m_count;

private:
  Item* _find(const T& v) {
    for (u32 i = 0; i < MaxSize; i++) {
      if (m_items[i].m_valid && m_items[i].m_data == v) {
        return &m_items[i];
      }
    }
    return nullptr;
  }

  Item* _find_next_free() {
    for (u32 i = 0; i < MaxSize; i++) {
      if (!m_items[i].m_valid) {
        return &m_items[i];
      }
    }
    return nullptr;
  }

  bool remove(Item& i) {
    if (!i.m_valid) {
      return false;
    }

    i.m_valid = false;
    m_count--;

    return true;
  }

public:
  explicit UnorderedCollection() {}

  u32 count() const {
    return m_count;
  }

  bool remove(const Iterator& i) {
    return remove(m_items[i.m_index]);
  }

  bool remove(const T& v) {
    Item* item = _find(v);

    if (nullptr == item) {
      return false;
    }

    return remove(*item);
  }

  T* add() {
    Item* p = _find_next_free();
    if (nullptr == p) {
      return nullptr;
    }

    m_count++;

    p->m_valid = true;
    return &p->m_data;
  }

  T* add(const T& v) {
    Item* p = _find_next_free();
    if (nullptr == p) {
      return nullptr;
    }
    
    m_count++;
    
    p->m_data = v;
    p->m_valid = true;
    return &p->m_data;
  }

  bool contains(const T& v) const {
    return _find(v) != nullptr;
  }

  Iterator begin() {
      return Iterator(*this, 0);
  }

  Iterator end() {
      return Iterator(*this, MaxSize);
  }
};

}

#endif  // CPRD_UNORDERED_COLLECTION_H
