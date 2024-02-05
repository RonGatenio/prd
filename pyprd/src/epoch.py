
import functools
import math
from dataclasses import dataclass
from typing import Type

@dataclass(frozen=True)
class Epoch:
    epoch: int | None = None

    @functools.cached_property
    def _epoch_internal(self):
        return self._epoch_value(self.epoch)

    def __int__(self) -> int:
        if self.epoch is None:
            raise TypeError("epoch is None, can't convert to int")
        return self.epoch

    @staticmethod
    def _epoch_value(obj: Type['Epoch'] | int | None) -> (int | float):
        match obj:
            case int():
                return obj
            case Epoch():
                return obj._epoch_internal
            case None:
                return -math.inf
            case _:
                raise TypeError('Unsupported type')
    
    def __eq__(self, other: Type['Epoch'] | int | None) -> bool:
        return self._epoch_internal == self._epoch_value(other)
    
    def __ne__(self, other: Type['Epoch'] | int | None) -> bool:
        return self._epoch_internal != self._epoch_value(other)

    def __gt__(self, other: Type['Epoch'] | int | None) -> bool:
        return self._epoch_internal > self._epoch_value(other)
    
    def __ge__(self, other: Type['Epoch'] | int | None) -> bool:
        return self._epoch_internal >= self._epoch_value(other)
    
    def __lt__(self, other: Type['Epoch'] | int | None) -> bool:
        return self._epoch_internal < self._epoch_value(other)
    
    def __le__(self, other: Type['Epoch'] | int | None) -> bool:
        return self._epoch_internal <= self._epoch_value(other)


@dataclass(frozen=True)
class ReversedEpoch:
    epoch: int | None = None

    @functools.cached_property
    def _epoch_internal(self):
        return self._epoch_value(self.epoch)

    def __int__(self) -> int:
        if self.epoch is None:
            raise TypeError("epoch is None, can't convert to int")
        return self.epoch

    @staticmethod
    def _epoch_value(obj: Type['ReversedEpoch'] | int | None) -> (int | float):
        match obj:
            case int():
                return obj
            case ReversedEpoch():
                return obj._epoch_internal
            case None:
                return math.inf
            case _:
                raise TypeError('Unsupported type')
    
    def __eq__(self, other: Type['ReversedEpoch'] | int | None) -> bool:
        return self._epoch_internal == self._epoch_value(other)
    
    def __ne__(self, other: Type['ReversedEpoch'] | int | None) -> bool:
        return self._epoch_internal != self._epoch_value(other)

    def __gt__(self, other: Type['ReversedEpoch'] | int | None) -> bool:
        return self._epoch_internal < self._epoch_value(other)
    
    def __ge__(self, other: Type['ReversedEpoch'] | int | None) -> bool:
        return self._epoch_internal <= self._epoch_value(other)
    
    def __lt__(self, other: Type['ReversedEpoch'] | int | None) -> bool:
        return self._epoch_internal > self._epoch_value(other)
    
    def __le__(self, other: Type['ReversedEpoch'] | int | None) -> bool:
        return self._epoch_internal >= self._epoch_value(other)
