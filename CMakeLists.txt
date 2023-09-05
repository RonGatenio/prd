cmake_minimum_required(VERSION 3.12)
project(PRD)

# Find LLVM
find_package(LLVM REQUIRED CONFIG)

# Set the path to the LLVMConfig.cmake file
list(APPEND CMAKE_PREFIX_PATH "${LLVM_CMAKE_DIR}")

# Add your LLVM pass source files from the "src" folder
file(GLOB MyPassSources src/**/*.cpp)

# Add your LLVM pass source files to the library
add_library(PRD MODULE ${MyPassSources})

# # Add your LLVM pass source files from the "src" folder
# add_library(PRD MODULE /app/src/prd/Prd.cpp)

# Link against LLVM libraries
target_link_libraries(PRD PRIVATE LLVMCore)

# Set the LLVM required flags
llvm_map_components_to_libnames(llvm_libs support core irreader)
target_link_libraries(PRD PRIVATE ${llvm_libs})

# Specify the LLVM include directories
include_directories(${LLVM_INCLUDE_DIRS})

# Export the necessary compilation flags for your pass
set_target_properties(PRD PROPERTIES COMPILE_FLAGS "${LLVM_DEFINITIONS}")

# Specify the LLVM libraries directory
link_directories(${LLVM_LIBRARY_DIRS})

# Install the LLVM pass
install(TARGETS PRD DESTINATION build)
