#ifndef CPRD_DEBUG_LOGGER_H
#define CPRD_DEBUG_LOGGER_H

#ifdef CPRD_DEBUG
#define _LOG(level, fmt, ...) Printf("[CPRD] [%s] [%d %s %s] " fmt "\n", level, cur_thread()->tid, __func__, __FILE__, __VA_ARGS__)
#else
#define _LOG(fmt, ...)
#endif

#ifndef CPRD_DEBUG_LEVEL
#define CPRD_DEBUG_LEVEL 2
#endif

#if CPRD_DEBUG_LEVEL >= 0
#define ERROR_LOG(fmt, ...) _LOG("ERROR", fmt, __VA_ARGS__)
#if CPRD_DEBUG_LEVEL >= 1
#define WARN_LOG(fmt, ...)  _LOG("WARN", fmt, __VA_ARGS__)
#if CPRD_DEBUG_LEVEL >= 2
#define DEBUG_LOG(fmt, ...) _LOG("DEBUG", fmt, __VA_ARGS__)
#if CPRD_DEBUG_LEVEL >= 3
#define TRACE_LOG(fmt, ...) _LOG("TRACE", fmt, __VA_ARGS__)
#else
#define TRACE_LOG(fmt, ...)
#endif
#else
#define DEBUG_LOG(fmt, ...)
#endif
#else
#define WARN_LOG(fmt, ...)
#endif
#else
#define ERROR_LOG(fmt, ...)
#endif

#endif  // CPRD_DEBUG_LOGGER_H
