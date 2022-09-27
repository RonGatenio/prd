from hbg_builder import HBGBuilder, nodes


_any_int = lambda x: int(x, 0)


class TraceParser:
    def __init__(self, trace_lines):
        self._trace = map(str.strip, trace_lines)

    @classmethod
    def from_file(cls, filename):
        with open(filename, 'r') as f:
            return cls(f.readlines())

    @staticmethod
    def _parse_line(hbgbuilder: HBGBuilder, line):
        tid, key, *args = line.split(':')
        tid = int(tid)

        if key == 'HB_EDGE':
            src_tid, src_epoch, dest_tid, dest_epoch = tuple(map(_any_int, args))
            hbgbuilder.add_happens_before_edge(nodes.EpochNode(src_tid, src_epoch), nodes.EpochNode(dest_tid, dest_epoch))
        elif key == 'EPOC_INC':
            from_epoch, to_epoch = tuple(map(_any_int, args))
            if from_epoch != to_epoch:
                hbgbuilder.add_node(nodes.EpochNode(tid, to_epoch))
        else:
            pc, address, size, *info = args
            pc = _any_int(pc)
            address = _any_int(address)
            size = _any_int(size)
            hbgbuilder.add_node(nodes.InstructionNode(tid, key, pc, address, size, ':'.join(info) if info else ''))

    @staticmethod
    def _is_comment_line(line):
        return line.startswith('#')

    def parse(self, debug=True) -> HBGBuilder:
        graph_builder = HBGBuilder()

        dbg_print = print if debug else lambda x: None

        for line in self._trace:
            # dbg_print(line)

            if not self._is_comment_line(line):
                try:
                    self._parse_line(graph_builder, line)
                except Exception as e:
                    dbg_print(f'Parse error {e}')
                    continue

        return graph_builder
