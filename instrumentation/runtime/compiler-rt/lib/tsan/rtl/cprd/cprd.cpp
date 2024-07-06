#include "sanitizer_common/sanitizer_stacktrace_printer.h"
#include "../tsan_symbolize.h"
#include "../tsan_defs.h"
#include "../tsan_rtl.h"
#include "cprd.h"


namespace cprd {


void Cprd::_s_log_loaded_modules() {
  static atomic_uint8_t printed_modules = {0};

  u8 cmp = 0;
  if (atomic_compare_exchange_strong(&printed_modules, &cmp, 1, memory_order_seq_cst)) {
    ListOfModules modules;
    modules.init();
    for (uptr i = 0; i < modules.size(); i++) {
      Printf("0:MODULE:%p:%p:%s\n", modules[i].base_address(), modules[i].max_executable_address(), modules[i].full_name());
    }
  }
}

void Cprd::_s_log_callstack(InternalScopedString& iss, ThreadState *thr, uptr pc) {
  VarSizeStackTrace trace;
  ObtainCurrentStack(thr, pc, &trace);
  for (uptr si = trace.size; si > 0; si--) {
    const uptr pc = trace.trace[si - 1];
    uptr pc1 = pc;
    // We obtain the return address, but we're interested in the previous
    // instruction.
    if ((pc & kExternalPCBit) == 0)
      pc1 = StackTrace::GetPreviousInstructionPc(pc);

    iss.append("%p%c", pc1, _s_callstack_delimiter);
  }
}

ALWAYS_INLINE USED
void Cprd::s_get_callstack_info(InternalScopedString& iss, ThreadState *thr, uptr pc, bool symbolize) {
  if (symbolize) {
    CaptureCurrentStack(&iss, thr, pc, _s_callstack_delimiter);
  } else {
    _s_log_loaded_modules();
    _s_log_callstack(iss, thr, pc);
  }
}

ALWAYS_INLINE USED
void Cprd::s_get_symbol_info(InternalScopedString& iss, ThreadState *thr, uptr pc, bool symbolize) {
  SymbolizedStack *ent = SymbolizeCode(pc);

  uptr pc1 = pc;
  if ((pc & kExternalPCBit) == 0)
    pc1 = StackTrace::GetPreviousInstructionPc(pc);

  if (symbolize) {
    SymbolizedStack *ent_prev_pc = SymbolizeCode(pc1);

    /*
      %f - function name
      %S - file/line/column
      %M - prints module basename and offset, if it is known, or PC.
    */
    RenderFrame(&iss, "%f %S ", 0, ent_prev_pc->info, false);
    RenderFrame(&iss, "%M", 0, ent->info, false);
  } else {
    iss.append("%p", pc1);
  }
}

Cprd& Cprd::_s_get_instance() {
  static Cprd cprd;
  return cprd;
}

Cprd& Cprd::s_get_instance() {
  ThreadState *thr = cur_thread();

  int prev_ignore_sync = thr->ignore_sync;
  thr->ignore_sync = 1;

  Cprd &cprd = Cprd::_s_get_instance();

  thr->ignore_sync = prev_ignore_sync;

  return cprd;
}

CprdThreadState& CprdThreadState::s_get_instance() {
  static thread_local CprdThreadState thread_state;
  return thread_state;
}

void Cprd::handle_open_file(const char* path, fd_t fd) {
  if (internal_strstr(path, _s_pm_pool_path_pattern) == nullptr) {
    return;
  }

  m_pm_pool_candidates.push_back(fd);
  DEBUG_LOG("In handle_open_file %s with fd %d", path, fd);
}

void Cprd::handle_close_file(fd_t fd) {
  if (m_pm_pool_candidates.remove(fd))
  DEBUG_LOG("In handle_close_file fd %d", fd);
}

void Cprd::handle_mmap(uptr addr, u32 size, fd_t fd) {
  dfsan_set_label(0, (void*)addr, RoundUpTo(size, GetPageSizeCached()));

  if (!m_pm_pool_candidates.contains(fd)) {
    return;
  }

  PMRegion region;
  region.begin = addr;
  region.end = addr + size;

  m_pm_regions.push_back(region);
  DEBUG_LOG("In handle_mmap; added PM region %p, size %p, fd %d", addr, size, fd);
}

void Cprd::handle_munmap(uptr addr, u32 size) {
  dfsan_set_label(0, (void*)addr, RoundUpTo(size, GetPageSizeCached()));

  PMRegion region;
  region.begin = addr;
  region.end = addr + size;

  if (m_pm_regions.remove(region)) {
    DEBUG_LOG("In handle_munmap; removed PM region %p, size %p", addr, size);
  }
}

ALWAYS_INLINE USED
bool Cprd::is_pm_address(uptr addr) {
  for (auto& region : m_pm_regions) {
    if (region.contains(addr)) {
      return true;
    }
  }
  return false;
}

ALWAYS_INLINE USED
void Cprd::instrument_memory_access(ThreadState *thr, uptr addr, uptr pc, 
  int kAccessSizeLog, bool kAccessIsWrite, bool kIsAtomic, bool kIsNonTemporal) {

  if (!is_pm_address(addr)) {
    return;
  }

  u64 event_id = CprdThreadState::s_get_instance().make_event_id();

  InternalScopedString res(2 * GetPageSizeCached());

  res.append("%llu:%d:%s:%p:%p:%d:",
            event_id,
            (int)thr->fast_state.tid(), 
            kAccessIsWrite ? "WRITE" : "READ", 
            (void*)pc, 
            (void*)addr,
            (int)(1 << kAccessSizeLog));
  s_get_symbol_info(res, thr, pc);

  res.append(":%d:%d", kIsAtomic, kIsNonTemporal);

  res.append("%c", _s_info_delimiter);
  s_get_callstack_info(res, thr, pc);

#if CPRD_SYMBOLIZE_PC
  res.append("# ");
  s_get_symbol_info(res, thr, pc, true);
#endif

  res.append("\n");
  Printf(res.data());

  // Program dependency analysis
#if CPRD_DEPENDENCY_ANALYSIS
  /*
    Note that this works because __tsan_write is called after the actual WRITE event
  */
  if (!kAccessIsWrite) {
    CprdThreadState::s_get_instance().df_mark_read(event_id, thr->fast_state.tid(), pc, addr, 1 << kAccessSizeLog);
  } else {
    CprdThreadState::s_get_instance().df_process_write(event_id, thr->fast_state.tid(), pc, addr, 1 << kAccessSizeLog);
  }
#endif

}

void Cprd::instrument_flush(ThreadState *thr, uptr pc, uptr addr) {
  addr = RoundDown(addr, kCacheLineSize);
  thr->flushes_cache.PushBack(addr);
}

void Cprd::instrument_fence(ThreadState *thr, uptr pc) {
  InternalScopedString res(2 * GetPageSizeCached());
  s_get_symbol_info(res, thr, pc);

  for (uptr i = 0; i < thr->flushes_cache.Size(); i++)
  {
    Printf("%d:FLUSH:%p:%p:%d:%s\n", thr->tid, (void*)pc, (void*)thr->flushes_cache[i], kCacheLineSize, res.data());
  }
  
  thr->flushes_cache.Reset();
}

void Cprd::log_happens_before_edge(u64 source_thread, u64 source_epoch, u64 target_thread, u64 target_epoch, const char* comment) {
  const char* comment_prefix = "  # ";
  
  if (!comment) {
    comment = "";
    comment_prefix = "";
  }

  Printf("%d:HB_EDGE:%d:%d:%d:%d%s%s\n", target_thread, source_thread, source_epoch, target_thread, target_epoch, comment_prefix, comment);
}

void Cprd::log_epoch_inc(u64 thread, u64 source_epoch, u64 target_epoch, const char* comment) {
  const char* comment_prefix = "  # ";
  
  if (!comment) {
    comment = "";
    comment_prefix = "";
  }

  Printf("%d:EPOC_INC:%d:%d%s%s\n", thread, source_epoch, target_epoch, comment_prefix, comment);
}

dfsan_label CprdThreadState::get_unused_label() {
  if (0 != m_unused_labels.Size()) {
    dfsan_label unused_label = m_unused_labels[m_unused_labels.Size() - 1];
    m_unused_labels.PopBack();

    TRACE_LOG("Using an unused label %x", unused_label);

    return unused_label;
  }

  dfsan_label label = dfsan_create_label(nullptr, nullptr);
  TRACE_LOG("Created new label %x", label);

  return label;
}

void CprdThreadState::remove_pending_read(PendingReadsCollection::Iterator& it) {
  m_unused_labels.PushBack(it->label);
  df_pending_reads.remove(it);
}

void CprdThreadState::df_mark_read(u64 event_id, u64 tid, uptr pc, uptr addr, u32 size) {
  dfsan_label label = dfsan_read_label((void*)addr, size);
  
  if (0 == label) {
    // Add new label if there isn't one already

    // if (DFSAN_MAX_LABELS < dfsan_get_label_count()) {
    //   TRACE_LOG("Labels count is %llx (max allowed is %llx), flushing dfsan (we will lose some PDs)", dfsan_get_label_count(), DFSAN_MAX_LABELS);
    //   Printf("Labels count is %p (max allowed is %p), flushing dfsan (we will lose some PDs)", dfsan_get_label_count(), DFSAN_MAX_LABELS);
    //   dfsan_flush();
    // }

    // InternalScopedString label_name(2 * GetPageSizeCached());
    // label_name.append("pd-%p-%p", addr, pc);
    
    // TRACE_LOG("Creating label %x - %s", label, label_name.data());
    // Printf("Creating label\n");

    // label = dfsan_create_label(label_name.data(), nullptr);
    label = get_unused_label();
    
    dfsan_add_label(label, (void*)addr, size); // not dfsan_set_label!
  }

  for (auto it = df_pending_reads.begin(); it != df_pending_reads.end(); ++it) {
    if (0 == --it->life) {
      remove_pending_read(it);
    }
  }

  auto *dependency_state = df_pending_reads.add();
  if (nullptr == dependency_state) {
    WARN_LOG("No more available pending states (max is %d)", PENDING_READS_MAX);
  } else {
    dependency_state->label = label;
    dependency_state->event_id = event_id;
    dependency_state->addr = addr;
    dependency_state->size = size;
    dependency_state->pc = pc;
    dependency_state->life = PENDING_READS_LIFE_MAX;
    TRACE_LOG("Added a pending read on %p at %p of size %d with label %x", addr, pc, size, label);
  }
}

void CprdThreadState::df_process_write(u64 event_id, u64 tid, uptr pc, uptr addr, u32 size) {
  dfsan_label label_content = dfsan_read_label((void*)addr, size);
  dfsan_label label_address = dfsan_get_label(addr);

  if ((0 == label_content) && (0 == label_address)) {
    // No label found
    return;
  }

  TRACE_LOG("labels for %p of size %d at %p: label_content=%x, label_address=%x", addr, size, pc, label_content, label_address);

  TRACE_LOG("Found %d pending reads", df_pending_reads.count());

  for (auto it = df_pending_reads.begin(); it != df_pending_reads.end(); ++it) {
    uptr write_addr_cacheline = RoundDown(addr, kCacheLineSize);
    uptr read_addr_cacheline  = RoundDown(it->addr, kCacheLineSize);

    // Ignore if variables are on the same cacheline
    if (write_addr_cacheline == read_addr_cacheline) {
      TRACE_LOG("Ignored - same cacheline %p", write_addr_cacheline);
      continue;
    }
    
    if (!dfsan_has_label(label_content, it->label) && !dfsan_has_label(label_address, it->label)) {
      TRACE_LOG("Ignored - no label %x", it->label);
      continue;
    }

    Printf("%llu:PD:%p:%llu:%p:%llu\n", tid, it->pc, it->event_id, pc, event_id);

    remove_pending_read(it);
  }

  TRACE_LOG("Left %d pending reads", df_pending_reads.count());
}

}
