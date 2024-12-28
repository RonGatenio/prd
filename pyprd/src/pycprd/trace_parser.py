import os
from typing import Set, Tuple
from collections import defaultdict

from .pdg import PDG, PDGBuilder, generate_mock_pdg_v2, pdg_distance
from .hbg import HBG, HBGBuilder
from .trace_event_info import TraceEventInfo
from .symbolizer import Symbolizer, Symbol
from .nodes import InstructionNode


_any_int = lambda x: int(x, 0)


class TraceParser:
    def __init__(self, trace_lines, name=None):
        self._trace = map(str.strip, trace_lines)
        self._hbg_builder = HBGBuilder()
        self._pdg_builder = PDGBuilder()
        self._events: dict[int, dict[int, InstructionNode]] = defaultdict(dict)     # tid -> idx -> node
        self._name = name
        self._pmem_range = None
        self._ignore_ranges: Set[Tuple[int, int]] = set()
        self._symbolizer: Symbolizer = Symbolizer()
    
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

    def _parse_line(self, line, line_number, debug=False, allow_keys=None):
        dbg_print = print if debug else lambda x: None
        
        line = line.removeprefix('<null>')
        
        if line.startswith(' ') or line.startswith('#') or line.startswith('[CPRD]'):
            return
        
        parts = line.split(':')
        
        if len(parts) < 2:
            # Invalid line
            dbg_print(f'Invalid line {line_number}')
            return

        args_index = 2
        tid, key = parts[:args_index]

        event_id = None
        if key.isdigit():
            args_index = 3
            event_id, tid, key = parts[:args_index]
            event_id = int(event_id)
        
        args = line.split('#')[0].strip().split(':')[args_index:]

        if not tid.isdigit():
            # Invalid tid
            dbg_print(f'Invalid tid {tid} in line {line_number}')
            return
        
        tid = int(tid)
        
        if allow_keys is not None and key not in allow_keys:
            return

        match key:
            case 'PD':
                if len(args) == 2:
                    read_pc, write_pc = tuple(map(_any_int, args))
                    self._pdg_builder.add_dependency_pc(read_node_pc=read_pc, write_node_pc=write_pc)
                else:
                    read_pc, read_event_id, write_pc, write_event_id = tuple(map(_any_int, args))
                    read_node = self._events[tid][read_event_id]
                    write_node = self._events[tid][write_event_id]
                    self._pdg_builder.add_dependency(read_node=read_node, write_node=write_node)
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
                self._symbolizer.add_module(name, start, end-start)
            case 'READ' | 'WRITE' | 'FLUSH':
                pc, address, size = parts[args_index:args_index+3]
                pc = _any_int(pc)
                address = _any_int(address)
                size = _any_int(size)
                
                is_atomic = is_non_temporal = False
                
                info = parts[args_index+3:]
                info = ':'.join(info) if info else ''
                
                if info.startswith('0x'):
                    info = info.split('#')[0].strip()
                    info = info.split('|')
                    
                    if ':' in info[0]:
                        addr, is_atomic, is_non_temporal = map(_any_int, info[0].split(':'))
                    else:
                        addr = _any_int(info[0])
                    callstack = tuple(map(_any_int, (info[1].strip(',').split(',') if len(info) > 1 else [])))

                    info = TraceEventInfo.from_addresses(addr, callstack, self._symbolizer)
                    
                    is_atomic = bool(is_atomic)
                    is_non_temporal = bool(is_non_temporal)
                else:
                    info = info.split('|')[0]
                    
                node = self._hbg_builder.add_instruction_node(key, tid, pc, address, size, info, line_number, is_atomic=is_atomic, is_non_temporal=is_non_temporal, event_id=event_id)
                if node.event_id is not None:
                    self._events[node.tid][node.event_id] = node
            case _:
                # Invalid key
                dbg_print(f'Invalid key {key} in line {line_number}')
                return

    def parse(self, debug=False, max_lines=None, allow_keys=None):
        for i, line in enumerate(self._trace):
            if max_lines and i > max_lines:
                break

            self._parse_line(line, i+1, debug=debug, allow_keys=allow_keys)

        return self

    def build_hbg(self, filter_volatile_nodes=False, debug=False, max_lines=None, make_daisy_chains=True, assert_dag=True, allow_keys=None) -> HBG:
        self.parse(debug=debug, max_lines=max_lines, allow_keys=allow_keys)

        return self._hbg_builder.build(filter_volatile_nodes=filter_volatile_nodes,
                                       pmem_range=self._pmem_range, make_daisy_chains=make_daisy_chains, ignore_ranges=self._ignore_ranges,
                                       assert_dag=assert_dag)
        
    def build_pdg(self, hbg: HBG, compare_to_mock=False) -> PDG:
        if not self._pdg_builder.total_dependencies:
            print('Fallback to mock PDG')
            return generate_mock_pdg_v2(hbg)

        pdg = self._pdg_builder.build(hbg)
        
        if compare_to_mock:
            _pdg = generate_mock_pdg_v2(hbg)
            distance, distance_per_read, missing_dependants = pdg_distance(hbg, _pdg, pdg)
            print(f'PDG - distance to mock {distance} - reads without dependants {missing_dependants}')
        
        return pdg
