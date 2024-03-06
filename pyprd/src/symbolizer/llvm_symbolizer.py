# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import subprocess


_LLVM_SYMBOLIZER_EXE = "llvm-symbolizer"


def get_symbol_information(module_path, module_offset):
    p = subprocess.Popen([_LLVM_SYMBOLIZER_EXE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate(f'{module_path} {module_offset}\n'.encode('utf-8'), 0.5)
    
    if stderr:
        return
    
    lines = stdout.decode('utf-8').split('\n')
    file, line, column = lines[1].split(':')
    return (lines[0], file, int(line), int(column))


# Not thread safe!
class LLVMSymbolizer(object):
    def __init__(self):
        self._llvm_symbolizer_subprocess = None
        self._started = 0

    def start(self):
        if self._started == 0:
            self._llvm_symbolizer_subprocess = subprocess.Popen(
                [_LLVM_SYMBOLIZER_EXE], stdout=subprocess.PIPE, stdin=subprocess.PIPE
            )
        
        self._started += 1

    def close(self):
        if self._started == 1:
            if self._llvm_symbolizer_subprocess:
                self._llvm_symbolizer_subprocess.kill()
                self._llvm_symbolizer_subprocess = None
        
        self._started = max(self._started - 1, 0)

    def __enter__(self):
        """Start the llvm symbolizer subprocess."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the llvm symbolizer subprocess."""
        self.close()

    def get_symbol_information(self, module_path, module_offset):
        p = subprocess.Popen([_LLVM_SYMBOLIZER_EXE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(f'{module_path} {module_offset}\n'.encode('utf-8'))
        
        if stderr:
            return []
        
        lines = stdout.decode('utf-8').split('\n')
        return [(lines[0], lines[1])]
        
        
        # if not self._started:
        #     raise Exception('Not started')
        
        # if not os.path.isfile(module_path):
        #     return []

        # self._llvm_symbolizer_subprocess.stdin.write(f'{module_path} {module_offset}\n'.encode('utf-8'))
        # self._llvm_symbolizer_subprocess.stdin.flush()
        # result = []
        # # Read till see new line, which is a symbol of end of output.
        # # One line of function name is always followed by one line of line number.
        # lines = self._llvm_symbolizer_subprocess.stdout.readlines()
        # if len(lines) < 2:
        #     print(lines)
        #     return []
        # return [(lines[0][:-1], lines[1][:-1])]
        # # while True:
        # #     line = .readline()
        # #     if line != "\n":
        # #         line_numbers = self._llvm_symbolizer_subprocess.stdout.readline()
        # #         result.append((line[:-1], line_numbers[:-1]))
        # #     else:
        # #         return result
