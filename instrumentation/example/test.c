#include <pthread.h>
#include <immintrin.h>

#define FLUSH(addr) _mm_clflush((void*)(addr))

#define FLUSHFENCE()  _mm_sfence()

volatile int GlobalX = 0;
volatile int GlobalY = 0;

void *Thread1(void *x) {
  // R(X)
  int temp = GlobalX;

  // W(Y)
  GlobalY = temp + 1;

  // F(Y)
  FLUSH(&GlobalY);
  FLUSHFENCE();
  
  return NULL;
}

void *Thread2(void *x) {
  // W(X)
  GlobalX = 1;

  // F(X)
  FLUSH(&GlobalX);
  FLUSHFENCE();
  
  return NULL;
}

#define COUNTOF(arr) sizeof((arr))/sizeof((arr)[0])

int main() {
    void* thread_funcs[] = {Thread1, Thread2};
    pthread_t t[COUNTOF(thread_funcs)];
    for (int _i = 0; _i < COUNTOF(thread_funcs); ++_i)
    {
        pthread_create(&t[_i], NULL, thread_funcs[_i], NULL);
    }
    for (int _i = 0; _i < COUNTOF(thread_funcs); ++_i)
    {
        pthread_join(t[_i], NULL);
    }
    return 0;
}
