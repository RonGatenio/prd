#ifndef CRPD_LOGGER_H
#define CRPD_LOGGER_H

#include "../tsan_defs.h"
#include "../tsan_rtl.h"
#include "sanitizer_common/sanitizer_file.h"

using namespace __tsan;

namespace cprd {

// class AutoCloseFile {
// private:
//     fd_t fd;

// static fd_t _s_open_file(const char *filename, FileAccessMode mode) {
//     fd_t fd = OpenFile(filename, mode);
//     if (kInvalidFd == fd) {
//         throw std::Excption()
//     }
// }

// public:
//     explicit AutoCloseFile(const char *filename) {};

// };

// enum PrdEventType {
//     PrdEventTypeHappensBeforeEdge,
//     PrdEventTypeEpocInc,
//     PrdEventTypeRead,
//     PrdEventTypeWrite,
//     PrdEventTypeFlush
// };

// class PrdEvent {
// public:

// private:
//     PrdEventType m_type;
// };

// typedef struct _PRD_EVENT {

// } PRD_EVENT, *PPPRD_EVENT;

// ALWAYS_INLINE void _Log(int tid, char* type) {
// }

// ALWAYS_INLINE void LogHappensBeforeEdge() {
// }

// }

// class Logger {
// private:
//     FileCloser logfile;

//     static fd_t _s_open_file(const char *filename, FileAccessMode mode) {
//         fd_t fd = OpenFile(filename, mode);
//         if (kInvalidFd == fd) {
//             throw 0; // TODO
//         }
//         return fd;
//     }

// public:
//     explicit Logger(const char *filename) :
//         logfile(_s_open_file(filename, WrOnly)) {}

//     void log_epoch() {};
//     void log_hb_edge() {};
//     void log_read_write() {};
//     void log_flush() {};
//     void log_fence() {};
// };

char _callstack_delimiter = ',';
char _info_delimiter = '|';

void get_symbol_info(InternalScopedString& iss, ThreadState* thr, uptr pc,
                     bool callstack = true, bool symbolize = false);

template <typename T, u32 MaxSize>
class Array {
 private:
  T m_data[MaxSize];
  u32 m_count;

  typedef bool (*predicate_function_t)(const T& arg);

 public:
  explicit Array() {}

  u32 Size() const { return m_count; }

  T& operator[](u32 i) {
    DCHECK_LT(i, m_count);
    return m_data[i];
  }

  const T& operator[](u32 i) const {
    DCHECK_LT(i, m_count);
    return m_data[i];
  }

  T* PushBack() {
    DCHECK_LT(m_count, MaxSize);
    T* p = &m_data[m_count++];
    internal_memset(p, 0, sizeof(*p));
    return p;
  }

  T* PushBack(const T& v) {
    DCHECK_LT(m_count, MaxSize);
    T* p = &m_data[m_count++];
    internal_memcpy(p, &v, sizeof(*p));
    return p;
  }

  void PopBack() {
    if (m_count > 0) {
      m_count--;
    }
  }

  bool IsInArray(const T& v) {
    for (u32 i = 0; i < m_count; i++) {
      if (m_data[i] == v) {
        return true;
      }
    }
    return false;
  }
};

/* PM regions */
#define PM_POOL_CAND_MAX 128

struct pm_region {
  uptr begin;
  uptr end;

  bool is_in_region(uptr addr) { return begin <= addr && addr < end; }
};

class Cprd {
 private:
  Array<fd_t, PM_POOL_CAND_MAX> m_pm_pool_candidates;
  Array<pm_region, PM_POOL_CAND_MAX> m_pm_regions;

  static constexpr const char* _s_pm_pool_path_pattern = "pmem";

  Cprd() = default;
  ~Cprd() = default;
  Cprd(const Cprd&)= delete;
  Cprd& operator=(const Cprd&)= delete;

 public:
  static Cprd& get_instance();

  void handle_open_file(const char* path, fd_t fd) {
    if (internal_strstr(path, _s_pm_pool_path_pattern) == nullptr) {
      return;
    }

    m_pm_pool_candidates.PushBack(fd);
    Printf("[*] In handle_open_file %s\n", path);
  }

  void handle_mmap(uptr addr, u32 size, fd_t fd) {
    if (!m_pm_pool_candidates.IsInArray(fd)) {
      return;
    }

    pm_region region;
    region.begin = addr;
    region.end = addr + size;

    m_pm_regions.PushBack(region);
    Printf("[*] In handle_mmap %p\n", addr);
  }

  bool is_pm_address(uptr addr) {
    for (u32 i = 0; i < m_pm_regions.Size(); i++) {
      if (m_pm_regions[i].is_in_region(addr)) {
        return true;
      }
    }
    return false;
  }
};

}  // namespace cprd

#endif  // CRPD_LOGGER_H
