import time
from contextlib import contextmanager
from config import DEFAULT_CACHELINE_SIZE


def get_cacheline_address(address, cacheline_size=DEFAULT_CACHELINE_SIZE):
    mask = ((1 << 64) - 1) * cacheline_size
    return address & mask


@contextmanager
def timeit(name):
    s = time.time()
    yield
    total = time.time() - s
    print(f'[*] {name:60} {total:.3f} sec')
