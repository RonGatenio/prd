from typing import Collection, Dict, Set
from .types import ThreadId, Cacheline
from . import utils


class DirtyCachelinesVector:
    def __init__(self, tid: ThreadId, tids: Collection[ThreadId]):
        self._tid = tid
        
        # A vector of dirty cachelines that we must update our inter-children with
        self._vector: Dict[ThreadId, Set[Cacheline]] = {t: set() for t in tids if t != tid}
        
        # Instead of updating the vector on every new cacheline that we see,
        # just update this temp buffer and dump it where needed when we update some child
        self._pending_dirty_cachelines: Set[Cacheline] = set()
    
    @property
    def tid(self) -> ThreadId:
        return self._tid
    
    @property
    def vector(self) -> Dict[ThreadId, Set[Cacheline]]:
        self._clear_pending()
        return self._vector
    
    def _clear_pending(self):
        if self._pending_dirty_cachelines:
            # Dump the pending dirty cachelines
            for tid, dirty_cachelines in self._vector.items():
                dirty_cachelines.update(self._pending_dirty_cachelines)
            
            # Clear the pending buffer
            self._pending_dirty_cachelines.clear()
    
    def get_dirty_cachelines(self, tid: ThreadId):
        return self.vector[tid]
    
    def set_cacheline_dirty(self, address: int, size: int = 1):
        """
        Set the variable's cachline as dirty
        """
        self._pending_dirty_cachelines.update(utils.get_cacheline_addresses(address, size))
        
    def update_child(self, child: 'DirtyCachelinesVector'):
        """
        Update the state of a child epoch node's DirtyCachelinesVector
        """
        
        # Assertions before update
        assert self.tid != child.tid, "Expecting to update an inter-child but got an intra-child"
        assert child.tid not in child._vector, "Expected child's tid to not be in the child node's vector"
        assert self.tid not in self._vector, "Expected tid to not be in my vector"
        
        # Update the child
        for tid, child_dirty_cachelines in child.vector.items():
            assert tid != child.tid, "Child is not expected to have a cell for itself"

            if tid == self.tid:
                continue
            
            child_dirty_cachelines.update(self.vector[tid])
            
        self._vector[child.tid].clear()
                
        # Assertions after an update
        assert not self._pending_dirty_cachelines, "Pending dirty cachelines are not expected"
        assert child.tid not in child._vector, "Expected tid to not be in the child node's vector"
        assert self.tid not in self._vector, "Expected tid to not be in my vector"
        assert self.tid in child._vector, "Expected child to have my tid in its vector"
        
    def merge(self, other: 'DirtyCachelinesVector'):
        """
        Merge the state of another DirtyCachelinesVector to me
        Use this when a thread wants to take the knowledge of an epoch node
        """
        assert self.tid == other.tid, "Expecting to merge with epochs from the same thread as me"
        assert not other._pending_dirty_cachelines, "Epoch node is not expected to have pending dirty cachelines"
        assert other.tid not in other._vector, "Expected tid to not be in the epoch node's vector"
        assert self.tid not in self._vector, "Expected tid to not be in my vector"
        
        for tid, dirty_cachelines in other._vector.items():
            self._vector[tid].update(dirty_cachelines)
