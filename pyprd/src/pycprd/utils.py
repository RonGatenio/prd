import time
import collections
from dataclasses import dataclass
from contextlib import contextmanager
from .config import DEFAULT_CACHELINE_SIZE


def get_cacheline_address(address, cacheline_size=DEFAULT_CACHELINE_SIZE) -> int:
    mask = ((1 << 64) - 1) * cacheline_size
    return address & mask


def get_cacheline_interval(address, size, cacheline_size=DEFAULT_CACHELINE_SIZE) -> tuple[int, int]:
    mask = ((1 << 64) - 1) * cacheline_size
    start = address & mask
    end = (address + size + cacheline_size - 1) & mask
    return start, end


@contextmanager
def timeit(name=None):
    @dataclass
    class Time:
        total: float

    t = Time(0)

    s = time.time()
    yield t
    total = time.time() - s

    t.total = total

    if name:
        print(f'[*] {name:60} {total:.3f} sec')


# TODO: move to another place
class DefaultDictByKey(collections.defaultdict):
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        if key not in self:
            self[key] = self.default_factory(key)
        return self[key]


def dict_printer(d: dict):
    pass
