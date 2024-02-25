from abc import ABC
from enum import Enum
from typing import Any
import utils


class NodeType(str, Enum):
    READ  = 'READ'
    WRITE = 'WRITE'
    FLUSH = 'FLUSH'
    EPOCH = 'EPOCH'

    @classmethod
    def is_instruction_type(cls, itype: 'NodeType'):
        return itype in (cls.READ, cls.WRITE, cls.FLUSH)

    @classmethod
    def is_read_write_type(cls, itype: 'NodeType'):
        return itype in (cls.READ, cls.WRITE)


class AbstractNode(ABC):
    def __init__(self, itype: NodeType, tid: int):
        super().__init__()
        self._itype = NodeType(itype)
        self._tid = int(tid)
        # self._tindex = int(tindex)

    @property
    def itype(self):
        """Return the instruction type"""
        return self._itype

    @property
    def tid(self):
        """Return the thread ID"""
        return self._tid

    def __repr__(self) -> str:
        itype = self.itype
        tid = self.tid
        return f'{self.__class__.__name__}({itype=}, {tid=})'


class EpochNode(AbstractNode):
    def __init__(self, tid: int, epoch: int):
        super().__init__(NodeType.EPOCH, tid)
        self._epoch = epoch

    @property
    def epoch(self):
        return self._epoch

    def __hash__(self) -> int:
        return hash((self.tid, self.epoch))

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, self.__class__):
            return (__o.tid, __o.epoch) == (self.tid, self.epoch)
        return False

    def __repr__(self) -> str:
        tid = self.tid
        epoch = self.epoch
        return f'{self.__class__.__name__}({tid=}, {epoch=})'


class InstructionNode(AbstractNode):
    def __init__(self, itype: NodeType, tid: int, pc: int, address: int, size: int, info: Any = None, trace_line_number: int = None):
        super().__init__(itype, tid)
        self._pc = pc
        self._address = address
        self._size = size
        self._info = info
        self._trace_line_number = trace_line_number

        assert size, "Size can't be 0"

    @property
    def instruction(self):
        return self.itype

    @property
    def pc(self):
        return self._pc

    @property
    def address(self):
        return self._address

    @property
    def size(self):
        return self._size

    @property
    def interval(self):
        return (self.address, self.address + self.size)

    @property
    def info(self):
        return self._info
    
    def is_interval_overlap(self, other: 'InstructionNode') -> bool:
        """
        Return True if the instructions' variables overlap
        """
        i1 = self.interval
        i2 = other.interval
        return max(i1[0], i2[0]) < min(i1[1], i2[1])
    
    def is_interval_contains(self, other: 'InstructionNode') -> bool:
        """
        Return True if other's variable is contained in self's interval
        """
        i1 = self.interval
        i2 = other.interval
        return i1[0] <= i2[0] < i2[1] <= i1[1]

    def get_cacheline_address(self, cacheline_size=utils.DEFAULT_CACHELINE_SIZE):
        return utils.get_cacheline_address(self.address, cacheline_size=cacheline_size)

    def get_cacheline_interval(self, cacheline_size=utils.DEFAULT_CACHELINE_SIZE):
        return utils.get_cacheline_interval(self.address, self.size, cacheline_size=cacheline_size)

    def __repr__(self) -> str:
        tid = self.tid
        instruction = self.instruction.name
        pc = self.pc
        address = self.address
        size = self.size
        info = self.info
        return f'{self.__class__.__name__}({tid=}, {instruction=}, {pc=:#x}, {address=:#x}, {size=}, {info=})'


class WriteNode(InstructionNode):
    def __init__(self, tid: int, pc: int, address: int, size: int, info: Any = None, trace_line_number: int = None):
        super().__init__(NodeType.WRITE, tid, pc, address, size, info, trace_line_number)


class ReadNode(InstructionNode):
    def __init__(self, tid: int, pc: int, address: int, size: int, info: Any = None, trace_line_number: int = None):
        super().__init__(NodeType.READ, tid, pc, address, size, info, trace_line_number)


class FlushNode(InstructionNode):
    def __init__(self, tid: int, pc: int, address: int, size: int, info: Any = None, trace_line_number: int = None):
        super().__init__(NodeType.FLUSH, tid, pc, address, size, info, trace_line_number)


def create_instruction_node(itype: NodeType,
                            tid: int,
                            pc: int,
                            address: int,
                            size: int,
                            info: Any = None,
                            trace_line_number: int = None) -> InstructionNode:
    cls = {
        NodeType.READ:  ReadNode,
        NodeType.WRITE: WriteNode,
        NodeType.FLUSH: FlushNode,
    }[itype]

    return cls(tid, pc, address, size, info, trace_line_number)
