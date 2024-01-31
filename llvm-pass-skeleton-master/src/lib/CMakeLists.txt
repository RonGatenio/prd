# Set the minimum required version of CMake
cmake_minimum_required(VERSION 3.12)

# Project name
project(RuntimeLib)

# Set the C++ standard to use
set(CMAKE_CXX_STANDARD 11)

# Specify the source files
set(SOURCES
    runtime.cpp
    # Add more source files as needed
)

# Set the compiler to clang++
set(CMAKE_CXX_COMPILER "clang++")

# Set compiler flags (optional)
# Example: Enable all warnings
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra")

# Create the shared library
# add_library(${PROJECT_NAME} SHARED ${SOURCES})
add_library(${PROJECT_NAME} STATIC ${SOURCES})

# Set the output directory for the shared library
# set_target_properties(${PROJECT_NAME} PROPERTIES
#     LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/bin
# )

# Specify include directories (if needed)
# Example: include_directories(include)

# Specify link directories (if needed)
# Example: link_directories(lib)

# Specify additional libraries to link (if needed)
# Example: target_link_libraries(${PROJECT_NAME} some_other_library)
