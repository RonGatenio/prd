
class Epoch(float):
    MIN = float('-inf')
    
    def __new__(cls, x=None):
        x = cls.MIN if x is None or x == cls.MIN else x
        return super().__new__(cls, x)
    
    def __eq__(self, other: 'Epoch') -> bool:
        return super().__eq__(self.__class__(other))
    
    def __ne__(self, other: 'Epoch') -> bool:
        return super().__ne__(self.__class__(other))

    def __gt__(self, other: 'Epoch') -> bool:
        return super().__gt__(self.__class__(other))
    
    def __ge__(self, other: 'Epoch') -> bool:
        return super().__ge__(self.__class__(other))
    
    def __lt__(self, other: 'Epoch') -> bool:
        return super().__lt__(self.__class__(other))
    
    def __le__(self, other: 'Epoch') -> bool:
        return super().__le__(self.__class__(other))


class ReversedEpoch(float):
    MIN = float('inf')
    
    def __new__(cls, x=None):
        x = cls.MIN if x is None or x == cls.MIN else x
        return super().__new__(cls, x)
    
    def __eq__(self, other: 'Epoch') -> bool:
        return super().__eq__(self.__class__(other))
    
    def __ne__(self, other: 'Epoch') -> bool:
        return super().__ne__(self.__class__(other))

    def __gt__(self, other: 'Epoch') -> bool:
        return super().__lt__(self.__class__(other))
    
    def __ge__(self, other: 'Epoch') -> bool:
        return super().__le__(self.__class__(other))
    
    def __lt__(self, other: 'Epoch') -> bool:
        return super().__gt__(self.__class__(other))
    
    def __le__(self, other: 'Epoch') -> bool:
        return super().__ge__(self.__class__(other))
