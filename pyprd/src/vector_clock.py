from collections import defaultdict
from typing import Dict
from epoch import Epoch, ReversedEpoch


ThreadId = int
AnyEpoch = Epoch | ReversedEpoch


class AbstractVectorClock:
    def __init__(self, tid: ThreadId):
        self._tid = tid
        self._epochs: Dict[ThreadId, AnyEpoch] = defaultdict(self.EpochClass)

    @property
    def tid(self) -> ThreadId:
        return self._tid

    @property
    def threads(self):
        return self._epochs.keys()

    def add_epoch(self, epoch: AnyEpoch):
        assert self._epochs[self._tid] < epoch, f"Can't change epoch {self._epochs[self._tid]} to {epoch}"
        self._epochs[self._tid] = self.EpochClass(epoch)

    def merge(self, other: 'VectorClock'):
        for tid in other.threads:
            if self._epochs[tid] < other._epochs[tid]:
                self._epochs[tid] = other._epochs[tid]

    def copy_from(self, other: 'VectorClock'):
        for tid in other.threads:
            self._epochs[tid] = other._epochs[tid]

    def get_epoch(self, tid: ThreadId) -> int | None:
        epoch = self._epochs.get(tid, None)
        if epoch == Epoch():
            return None
        return int(epoch)


class VectorClock(AbstractVectorClock):
    EpochClass = Epoch

    def is_happens_before(self, tid: ThreadId, epoch: AnyEpoch) -> bool:
        """
        Is the event at (tid, epoch) happens before this vector clock
        """
        return self._epochs[tid] >= self.EpochClass(epoch)


class ReversedVectorClock(AbstractVectorClock):
    EpochClass = ReversedEpoch

    def is_happens_after(self, tid: ThreadId, epoch: AnyEpoch) -> bool:
        """
        Is the event at (tid, epoch) happens after this vector clock
        """
        return self._epochs[tid] >= self.EpochClass(epoch)


class PersistencyVectorClock:
    def __init__(self, tid: ThreadId):
        self._tid = tid
        self._last_seen         = VectorClock(tid)
        self._last_persisted    = VectorClock(tid)

    @property
    def tid(self) -> ThreadId:
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

    def get_persisted_epoch(self, tid: ThreadId) -> int | None:
        return self._last_persisted.get_epoch(tid)
    
    def is_event_persisted(self, tid: ThreadId, epoch: Epoch) -> bool:
        return self._last_persisted.is_happens_before(tid, epoch)
    
    def is_persisted(self) -> bool:
        for tid in self.threads:
            if self._last_persisted.get_epoch(tid) != self._last_seen.get_epoch(tid):
                return False
        return True
