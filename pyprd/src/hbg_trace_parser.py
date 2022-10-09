from typing import Set, Tuple, List
from hbg import HBG, HBGBuilder
import nodes


_any_int = lambda x: int(x, 0)


class TraceParser:
    def __init__(self, trace_lines):
        self._trace = map(str.strip, trace_lines)
        self._nodes: List[nodes.AbstractNode] = []
        self._edges: Set[Tuple[nodes.AbstractNode, nodes.AbstractNode]] = set()

    @classmethod
    def from_file(cls, filename):
        with open(filename, 'r') as f:
            return cls(f.readlines())

    def _parse_line(self, line):
        line = line.split('#')[0].strip()
        tid, key, *args = line.split(':')
        tid = int(tid)

        if key == 'HB_EDGE':
            src_tid, src_epoch, dest_tid, dest_epoch = tuple(map(_any_int, args))
            self._edges.add((nodes.EpochNode(src_tid, src_epoch), nodes.EpochNode(dest_tid, dest_epoch)))
        elif key == 'EPOC_INC':
            from_epoch, to_epoch = tuple(map(_any_int, args))
            if from_epoch != to_epoch:
                self._nodes.append(nodes.EpochNode(tid, to_epoch))
        else:
            pc, address, size, *info = args
            pc = _any_int(pc)
            address = _any_int(address)
            size = _any_int(size)
            self._nodes.append(nodes.InstructionNode(tid, key, pc, address, size, ':'.join(info) if info else ''))

    @staticmethod
    def _is_comment_line(line):
        return line.startswith('#')

    def parse(self, debug=False, max_lines=None):
        dbg_print = print if debug else lambda x: None

        for i, line in enumerate(self._trace):
            if max_lines and i > max_lines:
                break
            # dbg_print(line)

            if not self._is_comment_line(line):
                try:
                    self._parse_line(line)
                except Exception as e:
                    dbg_print(f'Parse error {e}')
                    continue

        return self

    def filter_volatile_nodes(self):
        import intervaltree

        t = intervaltree.IntervalTree()

        for n in self._nodes:
            if n.itype == nodes.NodeType.FLUSH:
                n: nodes.InstructionNode
                t.addi(*n.interval)

        t.merge_overlaps(strict=False)

        def should_keep(n: nodes.AbstractNode):
            if n.itype not in (nodes.NodeType.READ, nodes.NodeType.WRITE):
                return True

            n: nodes.InstructionNode
            if t.overlaps_range(*n.interval):
                return True

            return False

        print(f'Total nodes before filter {len(self._nodes)}')
        self._nodes = list(filter(should_keep, self._nodes))
        print(f'Total nodes after filter  {len(self._nodes)}')

        return self

    def to_hbg(self, filter=True, debug=False) -> HBG:
        self.parse(debug=debug)
        if filter:
            self.filter_volatile_nodes()
        return HBGBuilder.from_elements(self._nodes, self._edges).build()
