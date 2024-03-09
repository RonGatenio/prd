import functools
import os
import shutil
from dataclasses import dataclass, field
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
        self._name = os.path.basename(path)
        
        self._module: lief.Binary = None
    
    @property
    def name(self):
        return self._name
    
    @functools.cached_property
    def path(self) -> str | None:
        _path = os.path.abspath(self._path)
        if os.path.isfile(_path):
            return os.path.abspath(_path)
        
        _path = os.path.abspath(os.path.join(LIB_DIR_PATH, self._name))
        if os.path.isfile(_path):
            return _path
        
        _path = shutil.which(self._name)
        if _path:
            return _path
        
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
        
        if not module or not module.module:
            return '??', address
        
        module_offset = address - start
        reloc_address = module_offset + module.module.imagebase
        
        for symbol in module.module.symbols:
            if symbol.value <= reloc_address < symbol.value + symbol.size:
                return symbol.name, reloc_address - symbol.value
            
        return module.name, module_offset
    
    def get_debug_info(self, address: int) -> Tuple[str, str, int, int] | None:
        start, end, module = self.get_module(address)
        
        if not module:
            return None
        
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


@dataclass(unsafe_hash=True)
class Symbol:
    address: int
    _symbolizer: Symbolizer = field(compare=False, repr=False)

    def __post_init__(self):
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
        
        start, end, module = self._symbolizer.get_module(self.address)
        if module:
            self._module = module.name
            self._module_path = module.path
            self._module_offset = self.address - start
            
        self._symbol, self._symbol_offset = self._symbolizer.get_symbol(self.address)
        
        dbg_info = self._symbolizer.get_debug_info(self.address)
        if dbg_info:
            self._symbol, self._file, self._line, self._column = dbg_info
        
        self._symbolized = True
    
    def __str__(self) -> str:
        self._symbolize()
        
        parts = [self._symbol]
        
        if self._file:
            filename = os.path.basename(self._file)
            line_col = f':{self._line}:{self._column}' if self._line is not None else ''
            parts.append(f'{filename}{line_col}')
            
        parts.append(f'({self._module}+0x{self._module_offset:x})')
        
        return ' '.join(parts)
