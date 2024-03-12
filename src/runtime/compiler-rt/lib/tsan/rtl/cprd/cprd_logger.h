#ifndef CRPD_LOGGER_H
#define CRPD_LOGGER_H

#include "sanitizer_common/sanitizer_file.h"
#include "../tsan_defs.h"
#include "../tsan_rtl.h"

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

void get_symbol_info(InternalScopedString& iss, ThreadState *thr, uptr pc, bool callstack = true, bool symbolize = false);

} // namespace cprd

#endif  // CRPD_LOGGER_H
