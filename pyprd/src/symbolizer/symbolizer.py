import os
import shutil
from dataclasses import dataclass
from typing import Tuple
import subprocess
import intervaltree
import lief


LIB_DIR_PATH         = os.environ.get('LIB_DIR_PATH', './lib')
LLVM_SYMBOLIZER_PATH = os.environ.get('LLVM_SYMBOLIZER_PATH', 'llvm-symbolizer')


LLVM_SYMBOLIZER_TIMEOUT   = 1.5
LLVM_SYMBOLIZER_MAX_TRIES = 4


class Module:
    def __init__(self, path):
        self._path = path
        self._real_path = None
        self._name = os.path.basename(path)
        
        self._module: lief.Binary = None
    
    @property
    def name(self):
        return self._name
    
    @property
    def path(self) -> str | None:
        if self._real_path:
            return self._real_path
        
        if os.path.isfile(self._path):
            self._real_path = self._path
            return self._real_path
        
        _path = shutil.which(self._name, LIB_DIR_PATH)
        if _path:
            self._real_path = _path
            return self._real_path
        
        _path = shutil.which(self._name)
        if _path:
            self._real_path = _path
            return self._real_path
        
        # raise FileNotFoundError(self._name)
        return None
    
    @property
    def module(self) -> lief.Binary | None:
        if not self._module and self.path:
            self._module = lief.parse(self.path)
        return self._module
    
    def __str__(self) -> str:
        return self._name


class Symbolizer:
    def __init__(self) -> None:
        self._modules = intervaltree.IntervalTree()
    
    def add_module(self, path: str, imagebase: str, size: int):
        self._modules.addi(imagebase, imagebase+size, Module(path))
    
    def get_module(self, address: int) -> Tuple[int, int, Module | None]:
        modules = self._modules.at(address)
        
        if not modules:
            return 0, 0, None
        
        assert len(modules) == 1
        
        start, end, module = modules.pop()
        return start, end, module
    
    def get_symbol(self, address: int) -> Tuple[str, int]:
        start, end, module = self.get_module(address)
        
        if not module:
            return '??', address
        
        module_offset = address - start
        reloc_address = module_offset + module.module.imagebase
        
        for symbol in module.module.symbols:
            if symbol.value <= reloc_address < symbol.value + symbol.size:
                return symbol.name, reloc_address - symbol.value
            
        return module.name, module_offset
    
    def get_debug_info(self, address: int) -> Tuple[str, str, int, int] | None:
        start, end, module = self.get_module(address)
        
        tries = 0
        while True:
            try:
                p = subprocess.Popen([LLVM_SYMBOLIZER_PATH], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = p.communicate(f'{module.path} {address - start}\n'.encode('utf-8'), LLVM_SYMBOLIZER_TIMEOUT)
                break
            except subprocess.TimeoutExpired:
                tries += 1
                if tries >= LLVM_SYMBOLIZER_MAX_TRIES:
                    raise
        
        if stderr:
            return None # '??', '??', 0, 0
        
        lines = stdout.decode('utf-8').split('\n')
        file, line, column = lines[1].split(':')
        return lines[0], file, int(line), int(column)


class Symbol:
    def __init__(self, address: int, symbolizer: Symbolizer) -> None:
        self._address = address
        self._symbolizer = symbolizer
        
        self._symbolized = False
        
        self._module: str = None
        self._module_path: str = None
        self._module_offset: int = None
        
        self._symbol: str = None
        self._symbol_offset: int = None
        
        self._file: str = None
        self._line: int = None
        self._column: int = None
    
    def _symbolize(self):
        if self._symbolized:
            return
        
        start, end, module = self._symbolizer.get_module(self._address)
        if module:
            self._module = module.name
            self._module_path = module.path
            self._module_offset = self._address - start
            
        self._symbol, self._symbol_offset = self._symbolizer.get_symbol(self._address)
        
        dbg_info = self._symbolizer.get_debug_info(self._address)
        if dbg_info:
            self._symbol, self._file, self._line, self._column = dbg_info
        
        self._symbolized = True
    
    @property
    def address(self) -> int:
        return self._address
    
    def __str__(self) -> str:
        self._symbolize()
        
        parts = [self._symbol]
        
        if self._file:
            filename = os.path.basename(self._file)
            line_col = f':{self._line}:{self._column}' if self._line is not None else ''
            parts.append(f'{filename}{line_col}')
            
        parts.append(f'({self._module}+0x{self._module_offset:x})')
        
        return ' '.join(parts)
