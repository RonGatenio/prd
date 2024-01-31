#!/bin/bash

export LLVM_INSTALL_PREFIX=$(llvm-config --prefix)
export LLVM_DEFINITIONS=$(llvm-config --cxxflags)
export LLVM_INCLUDE_DIRS=$(llvm-config --includedir)
export LLVM_LIBRARY_DIRS=$(llvm-config --libdir)
export LLVM_CMAKE_DIR=$(llvm-config --cmakedir)
