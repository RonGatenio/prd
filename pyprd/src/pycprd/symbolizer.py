import functools
import os
import shutil
from dataclasses import dataclass, field
from typing import Tuple, Dict
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
    
    @functools.cache
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
    
    @functools.cache
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

    _symbolizer: Symbolizer = field(compare=False, repr=False, hash=False)
    
    module: str             = field(default=None, init=False, compare=False, repr=False, hash=False)
    module_path: str        = field(default=None, init=False, compare=False, repr=False, hash=False)
    module_offset: int      = field(default=None, init=False, compare=False, repr=False, hash=False)
    
    symbol: str             = field(default=None, init=False, compare=False, repr=False, hash=False)
    symbol_offset: int      = field(default=None, init=False, compare=False, repr=False, hash=False)
    
    file: str               = field(default=None, init=False, compare=False, repr=False, hash=False)
    filename: str           = field(default=None, init=False, compare=False, repr=False, hash=False)
    line: int               = field(default=None, init=False, compare=False, repr=False, hash=False)
    column: int             = field(default=None, init=False, compare=False, repr=False, hash=False)
    
    def __post_init__(self):
        self._symbolized = False
    
    def _symbolize(self):
        if self._symbolized:
            return

        start, end, module = self._symbolizer.get_module(self.address)
        if module:
            self.module = module.name
            self.module_path = module.path
            self.module_offset = self.address - start
            
        self.symbol, self.symbol_offset = self._symbolizer.get_symbol(self.address)
        
        dbg_info = self._symbolizer.get_debug_info(self.address)
        if dbg_info:
            self.symbol, self.file, self.line, self.column = dbg_info
            self.filename = os.path.basename(self.file)
        
        self._symbolized = True
    
    @property
    def file_location_str(self) -> str:
        self._symbolize()
        
        if not self.file:
            return ''
        
        line_col = f':{self.line}:{self.column}' if self.line is not None else ''
        return f'{self.filename}{line_col}'
    
    @property
    def module_offset_str(self) -> str:
        self._symbolize()
        if not self.module:
            return ''
        return f'({self.module}+0x{self.module_offset:x})'

    def __str__(self) -> str:
        self._symbolize()
        
        parts = [self.symbol]
        
        if self.file_location_str:
            parts.append(self.file_location_str)
            
        parts.append(self.module_offset_str)
        
        return ' '.join(parts)
