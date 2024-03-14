// #include "sanitizer_common/sanitizer_file.h"
#include "sanitizer_common/sanitizer_stacktrace_printer.h"
#include "../tsan_symbolize.h"
#include "cprd_logger.h"

using namespace __tsan;

namespace cprd {


void log_loaded_modules() {
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

void log_callstack(InternalScopedString& iss, ThreadState *thr, uptr pc) {
  VarSizeStackTrace trace;
  ObtainCurrentStack(thr, pc, &trace);
  for (uptr si = trace.size; si > 0; si--) {
    const uptr pc = trace.trace[si - 1];
    uptr pc1 = pc;
    // We obtain the return address, but we're interested in the previous
    // instruction.
    if ((pc & kExternalPCBit) == 0)
      pc1 = StackTrace::GetPreviousInstructionPc(pc);

    iss.append("%p%c", pc1, _callstack_delimiter);
  }
}

ALWAYS_INLINE USED
void get_symbol_info(InternalScopedString& iss, ThreadState *thr, uptr pc, bool callstack, bool symbolize) {
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

  if (callstack) {
    iss.append("%c", _info_delimiter);

    if (symbolize) {
      CaptureCurrentStack(&iss, thr, pc, _callstack_delimiter);
    } else {
      log_loaded_modules();
      log_callstack(iss, thr, pc);
    }
  }
}

Cprd& Cprd::s_get_instance() {
  static Cprd cprd;
  return cprd;
}

}
