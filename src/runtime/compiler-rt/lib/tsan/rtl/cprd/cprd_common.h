#ifndef CPRD_COMMON_H
#define CPRD_COMMON_H

#include "../tsan_defs.h"

using namespace __tsan;

#define DEBUG_LOG(fmt, ...) Printf("[CPRD] [%d %s] " fmt "\n", cur_thread()->tid, __func__, __VA_ARGS__)

#endif  // CPRD_COMMON_H
