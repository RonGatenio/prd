#ifndef CRPD_LOGGER_H
#define CRPD_LOGGER_H

#include "../tsan_defs.h"
#include "../tsan_rtl.h"
#include "sanitizer_common/sanitizer_file.h"
#include "cprd_common.h"
#include "cprd_array.h"
#include "cprd_unordered_array.h"

typedef unsigned short dfsan_label;
typedef unsigned long long size_t;
extern "C" dfsan_label dfsan_create_label(const char *desc, void *userdata);
extern "C" void dfsan_add_label(dfsan_label label, void *addr, size_t size);
extern "C" void dfsan_set_label(dfsan_label label, void *addr, size_t size);
extern "C" dfsan_label dfsan_read_label(const void *addr, size_t size);
extern "C" int dfsan_has_label(dfsan_label label, dfsan_label elem);

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

void get_callstack_info(InternalScopedString& iss, ThreadState *thr, uptr pc, bool symbolize = false);

void get_symbol_info(InternalScopedString& iss, ThreadState *thr, uptr pc, bool symbolize = false);



/* PM regions */
#define PM_POOL_CAND_MAX 128
#define PENDING_READS_MAX 10000

struct pm_region {
  uptr begin;
  uptr end;

  bool operator==(const pm_region& other) const {
    return begin == other.begin && end == other.end;
  }

  bool contains(uptr addr) { return begin <= addr && addr < end; }
};


struct DependencyState {
  dfsan_label label;
  uptr addr;
  uptr size;
  uptr pc;
  u32 life;
};

typedef AddrHashMap<DependencyState, 31051> LabelsHashMap;

// This struct is stored in TLS.
class CprdThreadState {
 private:
  UnorderedArray<DependencyState, PENDING_READS_MAX> df_pending_reads;
  Vector<uptr> flushes_cache;

  CprdThreadState() = default;
  ~CprdThreadState() = default;
  CprdThreadState(const CprdThreadState&)= delete;
  CprdThreadState& operator=(const CprdThreadState&)= delete;

 public:
  static CprdThreadState& s_get_instance();

  void df_mark_read(uptr pc, uptr addr, u32 size) {
    dfsan_label label = dfsan_read_label((void*)addr, size);
    
    if (0 == label) {
      InternalScopedString label_name(2 * GetPageSizeCached());
      label_name.append("pd-%p-%p", addr, pc);
      
      TRACE_LOG("Creating label %x - %s", label, label_name.data());

      label = dfsan_create_label(label_name.data(), nullptr);     
      
      dfsan_add_label(label, (void*)addr, size); // not dfsan_set_label!
      // dfsan_set_label(label, (void*)addr, size); // not dfsan_set_label!
    }

    for (auto& df_pending_read : df_pending_reads) {
      if (0 == --df_pending_read.data.life) {
        df_pending_reads.remove_item(df_pending_read);
      }
    }

    auto *dependency_state = df_pending_reads.add();
    if (nullptr == dependency_state) {
      WARN_LOG("No more available pending states (max is %d)", PENDING_READS_MAX);
    } else {
      dependency_state->label = label;
      dependency_state->addr = addr;
      dependency_state->size = size;
      dependency_state->pc = pc;
      dependency_state->life = 100;
    }
  }

  void df_process_write(uptr pc, uptr addr, u32 size) {
    dfsan_label label = dfsan_read_label((void*)addr, size);

    if (0 == label) {
      return;
    }

    TRACE_LOG("Write has label %x", label);

    TRACE_LOG("Found %d pending reads", df_pending_reads.count());

    for (auto& df_pending_read : df_pending_reads) {
      if (dfsan_has_label(label, df_pending_read.data.label)) {
        Printf("PD:%p:%p\n", df_pending_read.data.pc, pc);
        df_pending_reads.remove_item(df_pending_read);
      }
    }
    TRACE_LOG("Left %d pending reads", df_pending_reads.count());
  }

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
  static Cprd& s_get_instance();

  void handle_open_file(const char* path, fd_t fd) {
    if (internal_strstr(path, _s_pm_pool_path_pattern) == nullptr) {
      return;
    }

    m_pm_pool_candidates.push_back(fd);
    DEBUG_LOG("In handle_open_file %s with fd %d", path, fd);
  }

  void handle_close_file(fd_t fd) {
    if (m_pm_pool_candidates.remove(fd))
    DEBUG_LOG("In handle_close_file fd %d", fd);
  }

  void handle_mmap(uptr addr, u32 size, fd_t fd) {
    dfsan_set_label(0, (void*)addr, RoundUpTo(size, GetPageSizeCached()));

    if (!m_pm_pool_candidates.contains(fd)) {
      return;
    }

    pm_region region;
    region.begin = addr;
    region.end = addr + size;

    m_pm_regions.push_back(region);
    DEBUG_LOG("In handle_mmap; added PM region %p, size %p, fd %d", addr, size, fd);
  }

  void handle_munmap(uptr addr, u32 size) {
    dfsan_set_label(0, (void*)addr, RoundUpTo(size, GetPageSizeCached()));

    pm_region region;
    region.begin = addr;
    region.end = addr + size;

    if (m_pm_regions.remove(region))
    DEBUG_LOG("In handle_munmap; removed PM region %p, size %p", addr, size);
  }

  ALWAYS_INLINE USED
  bool is_pm_address(uptr addr) {
    for (auto& region : m_pm_regions) {
      if (region.contains(addr)) {
        return true;
      }
    }
    return false;
  }

  ALWAYS_INLINE USED
  void instrument_memory_access(ThreadState *thr, uptr addr, uptr pc, 
    int kAccessSizeLog, bool kAccessIsWrite, bool kIsAtomic, bool kIsNonTemporal) {

    if (!is_pm_address(addr)) {
      return;
    }

    InternalScopedString res(2 * GetPageSizeCached());

    res.append("%d:%s:%p:%p:%d:", 
              (int)thr->fast_state.tid(), 
              kAccessIsWrite ? "WRITE" : "READ", 
              (void*)pc, 
              (void*)addr,
              (int)(1 << kAccessSizeLog));
    get_symbol_info(res, thr, pc);

    res.append(":%d:%d", kIsAtomic, kIsNonTemporal);

    res.append("%c", _info_delimiter);
    get_callstack_info(res, thr, pc);

#if CPRD_SYMBOLIZE_PC
    res.append("# ");
    get_symbol_info(res, thr, pc, true);
#endif

    res.append("\n");
    Printf(res.data());


    if (!kAccessIsWrite) {
      CprdThreadState::s_get_instance().df_mark_read(pc, addr, 1 << kAccessSizeLog);
    } else {
      CprdThreadState::s_get_instance().df_process_write(pc, addr, 1 << kAccessSizeLog);
    }

  }

  void instrument_flush(ThreadState *thr, uptr pc, uptr addr) {
    addr = RoundDown(addr, kCacheLineSize);
    thr->flushes_cache.PushBack(addr);
  }

  void instrument_fence(ThreadState *thr, uptr pc) {
    InternalScopedString res(2 * GetPageSizeCached());
    get_symbol_info(res, thr, pc);

    for (uptr i = 0; i < thr->flushes_cache.Size(); i++)
    {
      Printf("%d:FLUSH:%p:%p:%d:%s\n", thr->tid, (void*)pc, (void*)thr->flushes_cache[i], kCacheLineSize, res.data());
    }
    
    thr->flushes_cache.Reset();
  }
};

}  // namespace cprd

#endif  // CRPD_LOGGER_H
