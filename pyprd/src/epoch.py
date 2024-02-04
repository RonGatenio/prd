
from copy import copy


class Epoch(int):
    def __new__(cls, x=None):
        if isinstance(x, cls):
            return copy(x)
        self = super().__new__(cls, x or 0)
        self._is_min = x is None
        return self
    
    def __float__(self) -> float:
        if self._is_min:
            return float('-inf')
        return super().__float__()
    
    def __eq__(self, other: 'Epoch') -> bool:
        return float(self).__eq__(float(self.__class__(other)))
    
    def __ne__(self, other: 'Epoch') -> bool:
        return float(self).__ne__(float(self.__class__(other)))

    def __gt__(self, other: 'Epoch') -> bool:
        return float(self).__gt__(float(self.__class__(other)))
    
    def __ge__(self, other: 'Epoch') -> bool:
        return float(self).__ge__(float(self.__class__(other)))
    
    def __lt__(self, other: 'Epoch') -> bool:
        return float(self).__lt__(float(self.__class__(other)))
    
    def __le__(self, other: 'Epoch') -> bool:
        return float(self).__le__(float(self.__class__(other)))


class ReversedEpoch(int):
    def __new__(cls, x=None):
        if isinstance(x, cls):
            return copy(x)
        self = super().__new__(cls, x or 0)
        self._is_min = x is None
        return self
    
    def __float__(self) -> float:
        if self._is_min:
            return float('inf')
        return super().__float__()
    
    def __eq__(self, other: 'Epoch') -> bool:
        return float(self).__eq__(float(self.__class__(other)))
    
    def __ne__(self, other: 'Epoch') -> bool:
        return float(self).__ne__(float(self.__class__(other)))

    def __gt__(self, other: 'Epoch') -> bool:
        return float(self).__lt__(float(self.__class__(other)))
    
    def __ge__(self, other: 'Epoch') -> bool:
        return float(self).__le__(float(self.__class__(other)))
    
    def __lt__(self, other: 'Epoch') -> bool:
        return float(self).__gt__(float(self.__class__(other)))
    
    def __le__(self, other: 'Epoch') -> bool:
        return float(self).__ge__(float(self.__class__(other)))
