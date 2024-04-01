#include "sanitizer_common/sanitizer_stacktrace_printer.h"
#include "../tsan_symbolize.h"
#include "cprd_logger.h"


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

Cprd& Cprd::s_get_instance() {
  static Cprd cprd;
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

  InternalScopedString res(2 * GetPageSizeCached());

  res.append("%d:%s:%p:%p:%d:", 
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
    CprdThreadState::s_get_instance().df_mark_read(pc, addr, 1 << kAccessSizeLog);
  } else {
    CprdThreadState::s_get_instance().df_process_write(pc, addr, 1 << kAccessSizeLog);
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
  const char* comment_prefix = comment ? "  # " : "";
  Printf("%d:HB_EDGE:%d:%d:%d:%d%s%s\n", target_thread, source_thread, source_epoch, target_thread, target_epoch, comment_prefix, comment);
}

}
