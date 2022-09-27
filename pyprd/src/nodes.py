from abc import ABC
from enum import Enum


class NodeType(str, Enum):
    READ  = 'READ'
    WRITE = 'WRITE'
    FLUSH = 'FLUSH'
    EPOCH = 'EPOCH'


class AbstractNode(ABC):
    def __init__(self, itype: NodeType, tid: int):
        super().__init__()
        self._tid = int(tid)
        self._itype = itype

    @property
    def tid(self):
        return self._tid
    
    @property
    def itype(self):
        return self._itype

    def __repr__(self) -> str:
        tid = self.tid
        itype = self.itype
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
    def __init__(self, tid: int, instruction: NodeType, pc: int, address: int, size: int, info):
        super().__init__(instruction, tid)
        self._instruction = instruction
        self._pc = pc
        self._address = address
        self._size = size
        self._info = info

    @property
    def instruction(self):
        return self._instruction

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

    def __repr__(self) -> str:
        tid = self.tid
        instruction = self.instruction
        pc = self.pc
        address = self.address
        size = self.size
        info = self.info
        return f'{self.__class__.__name__}({tid=}, {instruction=}, {pc=:#x}, {address=:#x}, {size=}, {info=})'
