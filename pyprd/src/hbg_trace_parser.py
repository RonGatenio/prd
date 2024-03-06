import os
from typing import Set, Tuple
from hbg import HBG, HBGBuilder
from trace_event_info import TraceEventInfo
import intervaltree
from symbolizer.symbolizer import AddressInfo


_any_int = lambda x: int(x, 0)


class TraceParser:
    def __init__(self, trace_lines, name=None):
        self._trace = map(str.strip, trace_lines)
        self._hbg_builder = HBGBuilder()
        self._name = name
        self._pmem_range = None
        self._ignore_ranges: Set[Tuple[int, int]] = set()
        self._module_interval = intervaltree.IntervalTree()
    
    @property
    def name(self):
        return self._name
    
    @property
    def pmem_range(self):
        return self._pmem_range

    @classmethod
    def from_file(cls, filename):
        name = os.path.splitext(os.path.basename(filename))[0]
        with open(filename, 'r') as f:
            return cls(f.readlines(), name)
        
    def address_to_info(self, address: int) -> AddressInfo:
        module = self._module_interval.at(address)
        if not module:
            return
        
        assert len(module) == 1
        
        module_start, module_end, module = module.pop()
            
        return AddressInfo.from_address(module, module_start, address)

    def _parse_line(self, line, line_number=None, debug=False):
        dbg_print = print if debug else lambda x: None
        # line = line.split('#')[0].strip()
        
        parts = line.split(':')
        
        if len(parts) < 2:
            # Invalid line
            dbg_print(f'Invalid line {line_number}')
            return

        tid, key = parts[:2]
        args = line.split('#')[0].strip().split(':')[2:]

        if not tid.isdigit():
            # Invalid tid
            dbg_print(f'Invalid tid {tid} in line {line_number}')
            return
        
        tid = int(tid)

        match key:
            case 'HB_EDGE':
                src_tid, src_epoch, dst_tid, dst_epoch = tuple(map(_any_int, args))
                self._hbg_builder.add_happens_before_edge(src_tid, src_epoch, dst_tid, dst_epoch)
            case 'EPOC_INC':
                from_epoch, to_epoch = tuple(map(_any_int, args))
                if from_epoch != to_epoch:
                    self._hbg_builder.add_epoch_node(tid, to_epoch)
            case 'PMEM':
                start, size = tuple(map(_any_int, args))
                self._pmem_range = (start, start+size)
            case 'VOLATILE':
                start, size = tuple(map(_any_int, args))
                self._ignore_ranges.add((start, start+size))
            case 'MODULE':
                start, end = tuple(map(_any_int, args[:2]))
                name = args[2]
                self._module_interval.addi(start, end, name)
            case 'READ' | 'WRITE' | 'FLUSH':
                pc, address, size = parts[2:5]
                pc = _any_int(pc)
                address = _any_int(address)
                size = _any_int(size)
                
                info = parts[5:]
                info = ':'.join(info) if info else ''
                
                if info.startswith('0x'):
                    info = info.split('|')
                    addr = _any_int(info[0])
                    callstack = map(_any_int, (info[1].strip(',') if len(info) > 1 else '').split(','))
                    
                    info = self.address_to_info(addr)
                    if info:
                        info = TraceEventInfo(str(info), info.function, info.file, info.line, info.column, list(map(self.address_to_info, callstack)))
                    else:
                        info = TraceEventInfo()
                else:
                    info = TraceEventInfo.from_str(info)
                    
                self._hbg_builder.add_instruction_node(key, tid, pc, address, size, info, line_number)
            case _:
                # Invalid key
                dbg_print(f'Invalid key {key} in line {line_number}')
                return

    def parse(self, debug=False, max_lines=None):
        for i, line in enumerate(self._trace):
            if max_lines and i > max_lines:
                break

            self._parse_line(line, i, debug=debug)

        return self

    def to_hbg(self, filter_volatile_nodes=True, debug=False, max_lines=None, make_daisy_chains=True) -> HBG:
        self.parse(debug=debug, max_lines=max_lines)

        return self._hbg_builder.build(filter_volatile_nodes=filter_volatile_nodes,
                                       pmem_range=self._pmem_range, make_daisy_chains=make_daisy_chains)
