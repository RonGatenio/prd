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

    T& operator*() {
      return m_arr.m_data[m_i].data;
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

  T* add() {
    _Item* p = _find_next_free();
    if (nullptr == p) {
      return nullptr;
    }

    p->valid = true;
    return &p->data;
  }

  T* add(const T& v) {
    _Item* p = _find_next_free();
    if (nullptr == p) {
      return nullptr;
    }
    
    p->data = v;
    p->valid = true;
    return &p->data;
  }

  bool contains(const T& v) {
    return _find(v) != nullptr;
  }

  bool remove(const T& v) {
    _Item* item = _find(v);

    if (nullptr == item) {
      return false;
    }
    
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
