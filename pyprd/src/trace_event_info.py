from dataclasses import dataclass
from typing import Collection, Tuple
import os

from symbolizer.symbolizer import Symbolizer, Symbol


class TraceEventInfo:
    def __init__(self, symbol: Symbol, callstack: Collection[Symbol] = None):
        self._symbol = symbol
        self._callstack = callstack if callstack else tuple()

    @classmethod
    def from_addresses(cls, address: int, callstack: Collection[int], symbolizer: Symbolizer) -> 'TraceEventInfo':
        return cls(Symbol(address, symbolizer), tuple(Symbol(x, symbolizer) for x in callstack))

    @property
    def symbol(self) -> Symbol:
        return self._symbol
    
    @property
    def callstack(self) -> Collection[Symbol]:
        return self._callstack
    
    def __str__(self) -> str:
        return str(self._symbol)
    
    def full_info(self,
                  callstack_limit:      int|None        = None,
                  callstack_line_limit: int|None        = None,
                  one_line_callstack:   bool|None       = False,
                  callstack_top_func:   str|list|None   = None,
                  indent=0) -> str:
        callstack = tuple(map(str, self._callstack))
        
        callstack_limit = callstack_limit if callstack_limit is not None else len(callstack)

        if isinstance(callstack_top_func, str):
            callstack_top_func = [callstack_top_func]

        if callstack_top_func:
            for i, l in reversed(list(enumerate(callstack))):
                if any((f in l for f in callstack_top_func)):
                    callstack_limit = min(i+1, callstack_limit)
                    break

        def trunc(l):
            if callstack_line_limit is None or len(l) <= callstack_line_limit:
                return l
            return l[:callstack_line_limit] + '...'
        
        delim = '\n' if not one_line_callstack else ';'

        callstack = delim.join((f'{" "*indent}#{i:2} {trunc(c)}' for i, c in enumerate(callstack[:callstack_limit])))

        if not callstack:
            return str(self)
        
        if one_line_callstack:
            return f'{str(self)} | {callstack}'
        return f'{str(self)}\n{callstack}\n'
