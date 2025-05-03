from dataclasses import dataclass, field
import re
from typing import Sequence, List
from .symbolizer import Symbolizer, Symbol


@dataclass(frozen=True)
class TraceEventInfo:
    symbol: Symbol
    callstack: Sequence[Symbol] = field(default_factory=tuple)

    @classmethod
    def from_addresses(cls, address: int, callstack: Sequence[int], symbolizer: Symbolizer) -> 'TraceEventInfo':
        return cls(Symbol(address, symbolizer), tuple(Symbol(x, symbolizer) for x in callstack))
    
    def __str__(self) -> str:
        return str(self.symbol)
    
    def callstack_str(self,
                      max_frames:             int  | None             = None,
                      max_line_width:         int  | None             = None,
                      one_line:               bool | None             = False,
                      top_frame_symbol_regex: str  | List[str] | None = None,
                      indent:                 int                     = 0,
                      ) -> str:
        if not self.callstack:
            return ''

        callstack = tuple(map(str, self.callstack))
        
        max_frames = min(max_frames, len(callstack)) if max_frames is not None else len(callstack)

        if isinstance(top_frame_symbol_regex, str):
            top_frame_symbol_regex = [top_frame_symbol_regex]

        if top_frame_symbol_regex:
            for i, l in reversed(list(enumerate(callstack))):
                if any((re.search(pattern, l) for pattern in top_frame_symbol_regex)):
                    max_frames = min(i+1, max_frames)
                    break

        def trunc(l):
            if max_line_width is None or len(l) <= max_line_width:
                return l
            return l[:max_line_width] + '...'
        
        delim = '\n' if not one_line else ';'

        callstack = delim.join((f'{" "*indent}#{i:2} {trunc(c)}' for i, c in enumerate(callstack[:max_frames])))
        
        return callstack
    
    def full_info(self,
                  callstack_limit:      int  | None             = None,
                  callstack_line_limit: int  | None             = None,
                  one_line_callstack:   bool | None             = False,
                  callstack_top_func:   str  | List[str] | None = None,
                  indent:               int                     = 0
                  ) -> str:
        callstack = self.callstack_str(max_frames=callstack_limit,
                                       max_line_width=callstack_line_limit,
                                       one_line=one_line_callstack,
                                       top_frame_symbol_regex=callstack_top_func,
                                       indent=indent)
        if not callstack:
            return str(self)
        
        if one_line_callstack:
            return f'{str(self)} | {callstack}'
        return f'{str(self)}\n{callstack}\n'
