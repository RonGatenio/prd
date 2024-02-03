from collections import defaultdict
from typing import Dict
from epoch import EpochBase, Epoch, ReverseEpoch


ThreadId = int


class VectorClock:
    def __init__(self, tid: ThreadId, epoch_class: type[EpochBase]):
        self._tid = tid
        self._epochs: Dict[ThreadId, EpochBase] = defaultdict(epoch_class)

    @classmethod
    def create(cls, tid: ThreadId) -> 'VectorClock':
        return cls(tid, Epoch)

    @classmethod
    def create_reversed(cls, tid: ThreadId) -> 'VectorClock':
        return cls(tid, ReverseEpoch)

    @property
    def tid(self) -> ThreadId:
        return self._tid

    @property
    def threads(self):
        return self._epochs.keys()

    def add_epoch(self, epoch: EpochBase):
        assert self._epochs[self._tid] < epoch, f"Can't add past epoch {epoch} (last recorded epoch was {self._epochs[self._tid]})"
        self._epochs[self._tid] = epoch

    def merge(self, other: 'VectorClock'):
        for tid in other.threads:
            if self._epochs[tid] < other._epochs[tid]:
                self._epochs[tid] = other._epochs[tid]

    def copy_from(self, other: 'VectorClock'):
        for tid in other.threads:
            self._epochs[tid] = other._epochs[tid]

    def get_epoch(self, tid: ThreadId) -> EpochBase:
        return self._epochs[tid]

    def is_happens_before(self, tid: ThreadId, epoch: EpochBase) -> bool:
        return self._epochs[tid] >= epoch


class PersistencyVectorClock:
    def __init__(self, tid: ThreadId, epoch_class: type[EpochBase]):
        self._tid = tid
        self._last_seen         = VectorClock(tid, epoch_class)
        self._last_persisted    = VectorClock(tid, epoch_class)

    @classmethod
    def create(cls, tid: ThreadId) -> 'PersistencyVectorClock':
        return cls(tid, Epoch)

    @classmethod
    def create_reversed(cls, tid: ThreadId) -> 'PersistencyVectorClock':
        return cls(tid, ReverseEpoch)

    @property
    def tid(self) -> ThreadId:
        return self._tid

    @property
    def threads(self):
        # TODO: delete assert in the future
        assert (self._last_seen.threads | self._last_persisted.threads) == self._last_seen.threads, 'asserting for now, delete later'
        return self._last_seen.threads

    def add_epoch(self, epoch: EpochBase):
        self._last_seen.add_epoch(epoch)

    def flush(self):
        self._last_persisted.copy_from(self._last_seen)

    def merge(self, other: 'PersistencyVectorClock'):
        self._last_seen.merge(other._last_seen)
        self._last_persisted.merge(other._last_persisted)

    def get_persisted_epoch(self, tid: ThreadId) -> EpochBase:
        return self._last_persisted.get_epoch(tid)
    
    def is_event_persisted(self, tid: ThreadId, epoch: EpochBase) -> bool:
        return self._last_persisted.is_happens_before(tid, epoch)
    
    def is_persisted(self) -> bool:
        for tid in self.threads:
            if self._last_persisted.get_epoch(tid) != self._last_seen.get_epoch(tid):
                return False
        return True
