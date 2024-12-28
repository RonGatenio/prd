import re
import functools
import networkx as nx
import json
import argparse

from .trace_event_info import TraceEventInfo
from .trace_parser import TraceParser
from .hbg import HBG
from .nodes import AbstractNode, InstructionNode, ReadNode, WriteNode, FlushNode, NodeType


class Analyzer:
    def __init__(self, hbg: HBG) -> None:
        self._hbg = hbg
        
    @classmethod
    def from_trace_parser(cls, trace_parser: TraceParser, **build_hbg_kwargs):
        return cls(trace_parser.build_hbg(assert_dag=False, **build_hbg_kwargs))
    
    @classmethod
    def from_trace_file(cls, trace_file_path: str, **build_hbg_kwargs):
        return cls.from_trace_parser(TraceParser.from_file(trace_file_path), **build_hbg_kwargs)
    
    @property
    def hbg(self):
        return self._hbg
    
    def cycles(self):
        return nx.simple_cycles(self._hbg.graph)
    
    def analyze_cycles(self):
        G = self._hbg.graph
        for cycle in self.cycles():
            print(cycle)
            print('')
            # n, = cycle
            # # print(nx.get_node_attributes(self._hbg.graph, n))
            # print(list(nx.neighbors(self._hbg.graph, n)))
            # # print(list(self._hbg.graph.predecessors(n)))
            # print(list(self._hbg.get_inter_children(n)))
            # print(list(self._hbg.get_intra_child(n)))
            # # outgoing_edges = ((e, nx.get_edge_attributes(G, e)) for e in G.out_edges(n))
            # # print(list(outgoing_edges))
    
    def get_node_trace_info(self, node: InstructionNode) -> TraceEventInfo:
        if not isinstance(node.info, TraceEventInfo):
            raise Exception('invalid node info')
        return node.info
    
    def node_to_str(self, node: AbstractNode) -> str:
        if isinstance(node, (ReadNode, WriteNode)):
            return node.str_info
        return str(node)
    
    def is_flush_node(self, node: InstructionNode, other: InstructionNode) -> bool:
        return node.itype == NodeType.FLUSH and node.is_interval_contains(other)
    
    @functools.cache
    def get_nodes_by_symbol(self, symbol_regex: str):
        return {node for node in self._hbg.read_write_nodes if re.search(symbol_regex, str(self.get_node_trace_info(node).symbol))}
        
    def analyze_all_paths(self, write_node: WriteNode, read_node: ReadNode, dependent_node: WriteNode):
        for i, path in enumerate(nx.all_simple_paths(self._hbg.graph, write_node, read_node)):
            has_flush = any(map(functools.partialmethod(self.is_flush_node, other=write_node), path))
            print(f'Path {i+1}' + ('Has flush' if has_flush else ''))
            print('\n'.join((f'    {self.node_to_str(n)}' for n in path)))
            print('\n')
    
    def serialize_node(self, node: InstructionNode, callstack_top_regex: str  | list[str] | None = None):
        if not isinstance(node.info, TraceEventInfo):
            raise Exception('invalid node info')
        
        description = []
        
        description.append(node.str_info)
        
        callstack_str = node.info.callstack_str(top_frame_symbol_regex=callstack_top_regex)
        if callstack_str:
            description.append(f'```\n{callstack_str}\n```')
        
        return {
            'file': node.info.symbol.file,
            'description': '\n\n'.join(description),
            'line': node.info.symbol.line,
        }
    
    def nodes_to_tour(self, nodes: list[AbstractNode]):
        return json.dumps({
            "$schema": "https://aka.ms/codetour-schema",
            "title": "here",
            "steps": [self.serialize_node(node) for node in nodes if NodeType.is_instruction_type(node.itype)]
        })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace")
    
    args = parser.parse_args()
    
    analyzer = Analyzer.from_trace_file(args.trace, allow_keys=['EPOC_INC', 'HB_EDGE'])
    
    if not analyzer.hbg.is_directed_acyclic_graph():
        print(f'HBG is not a DAG')
    
    analyzer.analyze_cycles()


if __name__ == '__main__':
    main()
