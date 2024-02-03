
class Epoch(int):
    MIN = -1
    
    def __new__(cls, x=None):
        if x is None or x == cls.MIN:
            x = cls.MIN
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


class ReverseEpoch(int):
    MIN = -1

    def __new__(cls, x=None):
        if x is None or x == cls.MIN:
            x = cls.MIN
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
