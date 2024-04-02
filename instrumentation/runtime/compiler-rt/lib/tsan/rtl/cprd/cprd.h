#ifndef CRPD_LOGGER_H
#define CRPD_LOGGER_H

#include "dfsan/dfsan_interface.h"
#include "../tsan_defs.h"
#include "../tsan_rtl.h"
#include "cprd_common.h"
#include "cprd_array.h"
#include "cprd_unordered_array.h"

namespace cprd {

#define PM_POOL_CAND_MAX 128
#define PENDING_READS_MAX 10000
#define PENDING_READS_LIFE_MAX 100

struct PMRegion {
  uptr begin;
  uptr end;

  bool operator==(const PMRegion& other) const {
    return begin == other.begin && end == other.end;
  }

  bool contains(uptr addr) { return begin <= addr && addr < end; }
};

struct DependencyState {
  dfsan_label label;
  u64 event_id;
  uptr addr;
  uptr size;
  uptr pc;
  u32 life;
};

// This struct is stored in TLS.
class CprdThreadState {
 private:
  UnorderedArray<DependencyState, PENDING_READS_MAX> df_pending_reads;
  Vector<uptr> flushes_cache;
  u64 event_counter;

  CprdThreadState() = default;
  ~CprdThreadState() = default;
  CprdThreadState(const CprdThreadState&)= delete;
  CprdThreadState& operator=(const CprdThreadState&)= delete;

 public:
  static CprdThreadState& s_get_instance();

  u64 make_event_id() { return event_counter++; }
  void df_mark_read(u64 event_id, u64 tid, uptr pc, uptr addr, u32 size);
  void df_process_write(u64 event_id, u64 tid, uptr pc, uptr addr, u32 size);

};

class Cprd {
 private:
  Array<fd_t, PM_POOL_CAND_MAX> m_pm_pool_candidates;
  Array<PMRegion, PM_POOL_CAND_MAX> m_pm_regions;

  static constexpr const char* _s_pm_pool_path_pattern = "pmem";

  static constexpr const char _s_callstack_delimiter = ',';
  static constexpr const char _s_info_delimiter = '|';

  Cprd() = default;
  ~Cprd() = default;
  Cprd(const Cprd&)= delete;
  Cprd& operator=(const Cprd&)= delete;

  static void _s_log_callstack(InternalScopedString& iss, ThreadState *thr, uptr pc);
  static void _s_log_loaded_modules();

 public:
  static Cprd& s_get_instance();

  /********************************************************************
   * Trace Information (and Symbolizing)
  *********************************************************************/
  static void s_get_callstack_info(InternalScopedString& iss, ThreadState *thr, uptr pc, bool symbolize = false);
  static void s_get_symbol_info(InternalScopedString& iss, ThreadState *thr, uptr pc, bool symbolize = false);

  /********************************************************************
   * PM Regions Tracking
  *********************************************************************/
  void handle_open_file(const char* path, fd_t fd);
  void handle_close_file(fd_t fd);
  void handle_mmap(uptr addr, u32 size, fd_t fd);
  void handle_munmap(uptr addr, u32 size);

  /********************************************************************
   * Instrumentation
  *********************************************************************/
  bool is_pm_address(uptr addr);
  void instrument_memory_access(ThreadState *thr, uptr addr, uptr pc, 
    int kAccessSizeLog, bool kAccessIsWrite, bool kIsAtomic, bool kIsNonTemporal);
  void instrument_flush(ThreadState *thr, uptr pc, uptr addr);
  void instrument_fence(ThreadState *thr, uptr pc);

  // TODO: not used yet
  void log_happens_before_edge(u64 source_thread, u64 source_epoch, u64 target_thread, u64 target_epoch, const char* comment = nullptr);
};

}  // namespace cprd

#endif  // CRPD_LOGGER_H
