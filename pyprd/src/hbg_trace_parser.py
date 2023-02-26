import os
from hbg import HBG, HBGBuilder


_any_int = lambda x: int(x, 0)


class TraceParser:
    def __init__(self, trace_lines, name=None):
        self._trace = map(str.strip, trace_lines)
        self._hbg_builder = HBGBuilder()
        self._name = name
        self._pmem_range = None
    
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

    def _parse_line(self, line, line_number=None):
        line = line.split('#')[0].strip()
        tid, key, *args = line.split(':')
        tid = int(tid)

        if key == 'HB_EDGE':
            src_tid, src_epoch, dst_tid, dst_epoch = tuple(map(_any_int, args))
            self._hbg_builder.add_happens_before_edge(src_tid, src_epoch, dst_tid, dst_epoch)
        elif key == 'EPOC_INC':
            from_epoch, to_epoch = tuple(map(_any_int, args))
            if from_epoch != to_epoch:
                self._hbg_builder.add_epoch_node(tid, to_epoch)
        elif key == 'PMEM':
            start, size = tuple(map(_any_int, args))
            self._pmem_range = (start, start+size)
        else:
            pc, address, size, *info = args
            pc = _any_int(pc)
            address = _any_int(address)
            size = _any_int(size)
            self._hbg_builder.add_instruction_node(key, tid, pc, address, size, ':'.join(info) if info else '', line_number)

    @staticmethod
    def _is_comment_line(line):
        return line.startswith('#')

    def parse(self, debug=False, max_lines=None):
        dbg_print = print if debug else lambda x: None

        for i, line in enumerate(self._trace):
            if max_lines and i > max_lines:
                break

            if not self._is_comment_line(line):
                try:
                    self._parse_line(line, i)
                except Exception as e:
                    dbg_print(f'Parse error {e}')
                    continue

        return self

    def to_hbg(self, filter_volatile_nodes=True, debug=False, max_lines=None) -> HBG:
        self.parse(debug=debug, max_lines=max_lines)

        return self._hbg_builder.build(filter_volatile_nodes=filter_volatile_nodes,
                                       pmem_range=self._pmem_range)
