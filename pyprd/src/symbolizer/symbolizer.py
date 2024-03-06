import os
from typing import Tuple
from dataclasses import dataclass
import lief
import os

from symbolizer.llvm_symbolizer import LLVMSymbolizer, get_symbol_information


def _address_to_symbol(module: lief.Binary, image_base: int, address: int) -> Tuple[lief.Symbol, int]:
    address = address - image_base + module.imagebase

    for symbol in module.symbols:
        if symbol.value <= address < symbol.value + symbol.size:
            return symbol, address - symbol.value
        
    return '', address - module.imagebase


def address_to_symbol(module_filepath: str, image_base: int, address: int) -> Tuple[str, int]:
    default_symbol = (os.path.basename(module_filepath), address - image_base)
    
    if not os.path.isfile(module_filepath):
        return default_symbol
    
    module = lief.parse(module_filepath)
    if not module:
        return default_symbol
    
    address = address - image_base + module.imagebase

    for symbol in module.symbols:
        if symbol.value <= address < symbol.value + symbol.size:
            return symbol.name, address - symbol.value
        
    return default_symbol


@dataclass(frozen=True)
class AddressInfo:
    address: int
    module: str
    module_offset: int
    
    function: str = None
    function_offset: int = None
    
    file: str = None
    line: str = None
    column: str = None
    
    @classmethod
    def from_address(cls, module_filepath: str, image_base: int, address: int, symbolizer: LLVMSymbolizer | None = None) -> 'AddressInfo':
        module_offset = address - image_base
        
        symbol_name, symbol_offset = address_to_symbol(module_filepath, image_base, address)
        # module = lief.parse(module_filepath) if os.path.isfile(module_filepath) else None
        # symbol_name = symbol_offset = None
        # if module:
        #     symbol, symbol_offset = address_to_symbol(module, image_base, address)
        #     symbol_name = symbol.name
        
        file = line = column = None
        
        # if not symbolizer:
        #     symbolizer = LLVMSymbolizer()
            
        # with symbolizer:
        #     symbols = symbolizer.get_symbol_information(module_filepath, module_offset)
        #     # assert len(symbols) == 1
        #     if len(symbols) == 1:
        #         func, flc = symbols[0]
        #         flc = flc.split(':')
        #         file = flc[0]
        #         if len(flc) == 3:
        #             line, column = flc[1:3]
        symbols = get_symbol_information(module_filepath, module_offset)
        if symbols:
            func, file, line, column = symbols
            
        return cls(address, module_filepath, module_offset, symbol_name, symbol_offset, file, line, column)
    
    def __str__(self) -> str:
        modulename = os.path.basename(self.module)
        
        parts = [self.function]
        
        if self.file:
            filename = os.path.basename(self.file)
            line_col = f':{self.line}:{self.column}' if self.line is not None else ''
            parts.append(f'{filename}{line_col}')
            
        parts.append(f'({modulename}+0x{self.module_offset:x})')
        
        return ' '.join(parts)


@dataclass(frozen=True)
class Module:
    path: str
    imagebase: int
    max_executable_address: int
    


class ModuleParser:
    def __init__(self):
        self._modules = []
        
    # def add_module()
