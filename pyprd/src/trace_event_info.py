from dataclasses import dataclass
from typing import List
import os


@dataclass(frozen=True)
class TraceEventInfo:
    info: str = ''
    function: str = None
    file: str = None
    line: str = None
    column: str = None
    symbol: str = None
    callstack: List[str] = None

    @classmethod
    def from_str(cls, s: str) -> 'TraceEventInfo':
        if not s:
            return cls()
        
        parts = s.split('|')
        info = parts[0]
        callstack = parts[1].split(';')[:-2] if len(parts) > 1 else []

        function = file = line = column = symbol = None

        if '@' in info:
            function, flc, symbol = info.split('@')
            file, line, column = flc.split(':')

        def callstack_entry_parser(line):
            if not line:
                return ''
            parts = line.split(' ')
            flc = parts[-2].split(':')
            if len(flc) == 3:
                file, line, column = flc
                parts[-2] = ':'.join((os.path.basename(file), line, column))
            return ' '.join(parts)
        callstack = list(map(callstack_entry_parser, callstack))

        return cls(info, function, file, line, column, symbol, callstack)
    
    def __str__(self) -> str:
        if not self.function:
            return self.info
        
        return f'{self.function} {os.path.basename(self.file)}:{self.line}:{self.column} {self.symbol}'
    
    def full_info(self,
                  callstack_limit:      int|None    = None,
                  callstack_line_limit: int|None    = None,
                  one_line_callstack:   bool|None   = False,
                  callstack_top_func:   str|None    = None) -> str:
        callstack_limit = callstack_limit if callstack_limit is not None else len(self.callstack)

        if callstack_top_func:
            for i, l in reversed(list(enumerate(self.callstack))):
                if callstack_top_func in l:
                    callstack_limit = min(i+1, callstack_limit)
                    break

        def trunc(l):
            if callstack_line_limit is None or len(l) <= callstack_line_limit:
                return l
            return l[:callstack_line_limit] + '...'
        
        delim = '\n' if not one_line_callstack else ';'

        callstack = delim.join(map(trunc, self.callstack[:callstack_limit]))

        if one_line_callstack:
            return f'{str(self)} | {callstack}'
        return f'{str(self)}\n{callstack}'
