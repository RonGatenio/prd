
class Epoch(int):
    def __new__(cls, x=None):
        return super().__new__(cls, -1 if x is None else abs(x))


class ReverseEpoch(int):
    def __new__(cls, x=None):
        return super().__new__(cls, 1 if x is None else -abs(x))
