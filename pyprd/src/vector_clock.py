from collections import defaultdict
from typing import Callable, Dict
import math


ThreadId    = int
Epoch       = int


class VectorClock:
    def __init__(self, tid: ThreadId, compare_func: Callable[[Epoch, Epoch], bool], min_value: Epoch):
        self._tid = tid
        self._compare_func = compare_func
        self._epochs: Dict[ThreadId, Epoch] = defaultdict(lambda: min_value)

    @classmethod
    def create(cls, tid: ThreadId) -> 'VectorClock':
        return cls(tid, float.__lt__, -math.inf)

    @classmethod
    def create_reversed(cls, tid: ThreadId) -> 'VectorClock':
        return cls(tid, float.__gt__, math.inf)

    @property
    def tid(self) -> ThreadId:
        return self._tid

    @property
    def threads(self):
        return self._epochs.keys()

    def get_epoch(self, tid: ThreadId) -> Epoch:
        return self._epochs[tid]

    def add_epoch(self, epoch: Epoch):
        assert self._compare_func(self._epochs[self._tid], epoch), f"Can't add past epoch {epoch} (last recorded epoch was {self._epochs[self._tid]})"
        self._epochs[self._tid] = epoch

    def merge(self, other: 'VectorClock'):
        for tid in other.threads:
            if self._compare_func(self._epochs[tid], other._epochs[tid]):
                self._epochs[tid] = other._epochs[tid]

    def copy_from(self, other: 'VectorClock'):
        for tid in other.threads:
            self._epochs[tid] = other._epochs[tid]

    def is_happens_before(self, tid: ThreadId, epoch: Epoch) -> bool:
        return epoch == self._epochs[tid] or self._compare_func(epoch, self._epochs[tid])


class PersistencyVectorClock:
    def __init__(self, tid: ThreadId, compare_func: Callable[[Epoch, Epoch], bool], min_value: Epoch):
        self._tid = tid
        self._last_seen         = VectorClock(tid, compare_func, min_value)
        self._last_persisted    = VectorClock(tid, compare_func, min_value)

    @classmethod
    def create(cls, tid: ThreadId):
        return cls(tid, float.__lt__, -math.inf)

    @classmethod
    def create_reversed(cls, tid: ThreadId):
        return cls(tid, float.__gt__, math.inf)

    @property
    def tid(self):
        return self._tid

    @property
    def threads(self):
        # TODO: delete assert in the future
        assert (self._last_seen.threads | self._last_persisted.threads) == self._last_seen.threads, 'asserting for now, delete later'
        return self._last_seen.threads

    def add_epoch(self, epoch: Epoch):
        self._last_seen.add_epoch(epoch)

    def flush(self):
        self._last_persisted.copy_from(self._last_seen)

    def merge(self, other: 'PersistencyVectorClock'):
        self._last_seen.merge(other._last_seen)
        self._last_persisted.merge(other._last_persisted)

    def get_persisted_epoch(self, tid: ThreadId) -> Epoch:
        return self._last_persisted.get_epoch(tid)
    
    def is_persisted(self, tid: ThreadId, epoch: Epoch) -> bool:
        return self._last_persisted.is_happens_before(tid, epoch)
