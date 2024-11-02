import json
import os
from .nodes import AbstractNode, InstructionNode
from .trace_event_info import TraceEventInfo


class CodeTour:
    def __init__(self, title):
        self._title = title
        self._steps = []
        
    @property
    def title(self):
        return self._title
    
    def set_title(self, title):
        self._title = title
    
    @property
    def filename(self):
        return f'{self._title}.tour'
    
    def add_step(self, filename, line, description):
        self._steps.append({
            'file': filename,
            'description': description,
            'line': line,
        })
        
    def add_node(self, node: AbstractNode, callstack_top_regex: str  | list[str] | None = None):
        if not isinstance(node, InstructionNode):
            return
        
        node: InstructionNode
        
        if not isinstance(node.info, TraceEventInfo):
            raise Exception('invalid node info')
        
        description = []
        description.append(node.str_info)
        
        callstack_str = node.info.callstack_str(top_frame_symbol_regex=callstack_top_regex)
        if callstack_str:
            description.append(f'```\n{callstack_str}\n```')
        
        self.add_step(node.info.symbol.filename, node.info.symbol.line, '\n\n'.join(description))
        
    def create(self) -> dict:
        return {
            "$schema": "https://aka.ms/codetour-schema",
            "title": self._title,
            "steps": self._steps,
        }
        
    def to_file(self, folder=None):
        folder = folder if folder else '.tours'
        
        if not os.path.exists(folder):
            os.makedirs(folder)
        
        with open(os.path.join(folder, self.filename), 'w') as f:
            json.dump(self.create(), f, indent=4)
