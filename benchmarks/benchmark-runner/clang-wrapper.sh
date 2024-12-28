#!/bin/bash
# Wrapper script for clang

# Path to the actual clang compiler
REAL_CLANG="clang"

# Additional flags to append during build
EXTRA_FLAGS="-fpass-plugin=/app/build/bin/PrdPass.so -mclwb -mclflushopt -dfsan-abilist=/app/benchmarks/benchmark-runner/libevent_abilist.txt"

# Flags to append during linking
LINK_FLAGS="-l:/app/build/bin/cprd-x86_64.a -fuse-ld=gold -z muldefs -lm -lstdc++ -pthread"

# Function to check if we are in the linking stage
is_linking() {
    # If no -c flag and output is not an object file, assume linking
    for arg in "$@"; do
        if [[ "$arg" == "-c" ]]; then
            return 1  # Compiling
        fi
    done
    return 0  # Linking
}

# Decide whether to add custom flags
if [[ "$ENABLE_PRD" == "true" ]]; then
    # Decide if we are compiling or linking
    if is_linking "$@"; then
        # Linking stage
        exec "$REAL_CLANG" "$@" $EXTRA_FLAGS $LINK_FLAGS
    else
        # Compilation stage
        exec "$REAL_CLANG" "$@" $EXTRA_FLAGS
    fi
else
    # Do not add extra flags
    exec "$REAL_CLANG" "$@"
fi
