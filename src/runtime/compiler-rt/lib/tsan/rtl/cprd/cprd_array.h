#ifndef CPRD_ARRAY_H
#define CPRD_ARRAY_H

#include "cprd_common.h"

namespace cprd {

/*  Array class
    not thread safe!
    always grows
*/
template <typename T, u32 MaxSize>
class Array {
private:
  struct _Item {
    bool valid;
    T data;
  };

  class Iterator {
  private:
    Array& m_arr;
    u32 m_i;

  public:
    Iterator(Array& arr, u32 i) : m_arr(arr), m_i(i) {}

    Iterator& operator++() {
      for (u32 i = m_i; i < m_arr.m_count; i++) {
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
  u32 m_count;

private:
  _Item* _find(const T& v) {
    for (u32 i = 0; i < m_count; i++) {
      if (m_data[i].valid && m_data[i].data == v) {
        return &m_data[i];
      }
    }
    return nullptr;
  }

public:
  explicit Array() {}

  T* push_back() {
    DCHECK_LT(m_count, MaxSize);
    _Item& p = m_data[m_count++];
    internal_memcpy(&p.data, 0, sizeof(p.data));
    p.valid = true;
    return &p.data;
  }

  T* push_back(const T& v) {
    DCHECK_LT(m_count, MaxSize);
    _Item& p = m_data[m_count++];
    internal_memcpy(&p.data, &v, sizeof(p.data));
    p.valid = true;
    return &p.data;
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
      return Iterator(*this, m_count);
  }
};

}

#endif  // CPRD_ARRAY_H
