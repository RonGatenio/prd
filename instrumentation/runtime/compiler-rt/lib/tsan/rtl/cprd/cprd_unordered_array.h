#ifndef CPRD_UNORDERED_ARRAY_H
#define CPRD_UNORDERED_ARRAY_H

#include "cprd_common.h"

namespace cprd {

/*  fixed sized UnorderedArray class
    not thread safe!
*/
template <typename T, u32 MaxSize>
class UnorderedArray {
private:
  struct _Item {
    bool valid;
    T data;
  };

  class Iterator {
  private:
    UnorderedArray& m_arr;
    u32 m_i;

  public:
    Iterator(UnorderedArray& arr, u32 i) : m_arr(arr), m_i(i) {}

    Iterator& operator++() {
      for (u32 i = m_i; i < MaxSize; i++) {
        m_i++;
        if (m_arr.m_data[m_i].valid) {
          break;
        }
      }

      return *this;
    }

    _Item& operator*() {
      return m_arr.m_data[m_i];
    }

    bool operator==(const Iterator& other) const {
      return m_i == other.m_i;
    }

    bool operator!=(const Iterator& other) const {
      return !(*this == other);
    }
  };

private:
  _Item m_data[MaxSize];
  u32 m_count;

private:
  _Item* _find(const T& v) {
    for (u32 i = 0; i < MaxSize; i++) {
      if (m_data[i].valid && m_data[i].data == v) {
        return &m_data[i];
      }
    }
    return nullptr;
  }

  _Item* _find_next_free() {
    for (u32 i = 0; i < MaxSize; i++) {
      if (!m_data[i].valid) {
        return &m_data[i];
      }
    }
    return nullptr;
  }

public:
  explicit UnorderedArray() {}

  u32 count() {
    return m_count;
  }

  void remove_item(_Item& i) {
    if (i.valid) {
      i.valid = false;
      m_count--;
    }
  }

  T* add() {
    _Item* p = _find_next_free();
    if (nullptr == p) {
      return nullptr;
    }

    m_count++;

    p->valid = true;
    return &p->data;
  }

  T* add(const T& v) {
    _Item* p = _find_next_free();
    if (nullptr == p) {
      return nullptr;
    }
    
    m_count++;
    
    p->data = v;
    p->valid = true;
    return &p->data;
  }

  bool contains(const T& v) {
    return _find(v) != nullptr;
  }

  bool remove_at(const u32 i) {
    if (i >= MaxSize) {
      return false;
    }

    if (!m_data[i].valid) {
      return false;
    }
    
    m_count--;
    m_data[i].valid = false;
    return true;
  }

  bool remove(const T& v) {
    _Item* item = _find(v);

    if (nullptr == item) {
      return false;
    }
    
    m_count--;

    item->valid = false;
    return true;
  }

  Iterator begin() {
      return Iterator(*this, 0);
  }

  Iterator end() {
      return Iterator(*this, MaxSize);
  }
};

}

#endif  // CPRD_UNORDERED_ARRAY_H
