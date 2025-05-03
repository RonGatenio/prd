cmake_minimum_required(VERSION 3.6)
# project(Pass)

# LLVM uses C++17.
set(CMAKE_CXX_STANDARD 17)

# Add LLVM cmake folder to search path
list(INSERT CMAKE_MODULE_PATH 0 "$ENV{LLVM_CMAKE_DIR}")

# Load LLVMConfig.cmake. If this fails, consider setting `LLVM_DIR` to point
# to your LLVM installation's `lib/cmake/llvm` directory.
find_package(LLVM REQUIRED CONFIG)

# Include the part of LLVM's CMake libraries that defines
# `add_llvm_pass_plugin`.
include(AddLLVM)

# Use LLVM's preprocessor definitions, include directories, and library search
# paths.
add_definitions($ENV{LLVM_DEFINITIONS})
include_directories($ENV{LLVM_INCLUDE_DIRS})
link_directories($ENV{LLVM_LIBRARY_DIRS})

add_definitions(-DAPP_SHARE="$ENV{APP_SHARE}")

# Our pass lives in this subdirectory.
add_subdirectory(prd)
add_subdirectory(dfsan)
