#####################################################################
# Setup stage
#####################################################################

FROM ubuntu:latest AS setup

# Set LLVM version
ENV LLVM_VERSION 14

# Install dev packages
RUN apt-get update && apt-get install -y llvm-${LLVM_VERSION} llvm-${LLVM_VERSION}-dev clang-${LLVM_VERSION}
RUN apt install -y cmake
RUN apt install -y python3-pip
RUN apt install -y build-essential libboost-all-dev libpapi-dev

# Install PMDK
RUN apt install -y libpmem-dev
RUN apt install -y libpmemobj-cpp-dev

# Install tools packages
RUN apt install -y dos2unix mlocate less

# Install jemalloc and tbb
RUN apt install -y libtbb-dev libjemalloc-dev

# Set env
ENV PATH /usr/lib/llvm-${LLVM_VERSION}/bin:$PATH

RUN ln -s /usr/include/llvm-${LLVM_VERSION} /usr/include/llvm
RUN ln -s /usr/include/llvm-c-${LLVM_VERSION} /usr/include/llvm-c

RUN echo . /app/instrumentation/scripts/setup-env.sh >> ~/.bashrc


#####################################################################
# Build stage
#####################################################################

FROM setup AS build

# Create a working directory
WORKDIR /app

# Copy instrumentation folder to container
COPY instrumentation /app/instrumentation

# Build pass and runtime lib
RUN /app/instrumentation/scripts/build.sh

# Add bin path to PATH
ENV PATH /app/build/bin:$PATH

# Copy pyprd folder to container
COPY pyprd /app/pyprd

# Install pyprd
WORKDIR /app/pyprd
RUN python3 setup.py install


#####################################################################
# Benchmarks stage
#####################################################################

FROM build AS benchmarks

# Copy from build stage
COPY --from=build /app /app

# Copy benchmarks folder
COPY benchmarks /app/benchmarks

# Make results compilations folder
ENV CPRD_RESULTS_BIN /app/results/bin
RUN mkdir -p ${CPRD_RESULTS_BIN}

# Make results traces folder
ENV CPRD_RESULTS_TRACES /app/results/traces
RUN mkdir -p ${CPRD_RESULTS_TRACES}

# Make results races folder
ENV CPRD_RESULTS_RACES /app/results/races
RUN mkdir -p ${CPRD_RESULTS_RACES}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# RECIPE (Converting Concurrent DRAM Indexes to Persistent-Memory Indexes)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
WORKDIR /app/benchmarks/RECIPE

RUN dos2unix *.sh
RUN ./compile.sh
RUN ./run.sh ; exit 0
RUN cp *.trace ${CPRD_RESULTS_TRACES}

RUN pycprd ${CPRD_RESULTS_TRACES}/pclht.trace          > ${CPRD_RESULTS_RACES}/pclht.races
# RUN pycprd ${CPRD_RESULTS_TRACES}/pclht-recovery.trace > ${CPRD_RESULTS_RACES}/pclht-recovery.races

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# CCEH (Cacheline-Concious Extendible Hashing)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
WORKDIR /app/benchmarks/CCEH

RUN dos2unix *.sh
RUN ./compile.sh
RUN ./run_pmdk.sh ; exit 0
RUN cp *.trace ${CPRD_RESULTS_TRACES}

RUN pycprd ${CPRD_RESULTS_TRACES}/multi_threaded_cceh.trace          > ${CPRD_RESULTS_RACES}/cceh.races
# RUN pycprd ${CPRD_RESULTS_TRACES}/multi_threaded_cceh-recovery.trace > ${CPRD_RESULTS_RACES}/cceh-recovery.races

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# FAST-FAIR (Failure-Atomic ShifT(FAST) and Failure-Atomic In-place Rebalancing(FAIR))
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
WORKDIR /app/benchmarks/FAST_FAIR

RUN dos2unix *.sh
RUN ./compile_pmdk.sh
RUN ./run_pmdk.sh ; exit 0
RUN cp *.trace ${CPRD_RESULTS_TRACES}

RUN pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk.trace                > ${CPRD_RESULTS_RACES}/fastfair.races
# RUN pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk-recovery.trace       > ${CPRD_RESULTS_RACES}/fastfair-recovery.races
RUN pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk-mixed.trace          > ${CPRD_RESULTS_RACES}/fastfair-mixed.races
# RUN pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk-mixed-recovery.trace > ${CPRD_RESULTS_RACES}/fastfair-mixed-recovery.races


#####################################################################
# Example stage
#####################################################################

# FROM build AS example

# COPY --from=build /app /app

# RUN clang -O0 -g -fpass-plugin=/app/build/bin/PrdPass.so -I/app/instrumentation/example/ /app/instrumentation/example/test.c /app/instrumentation/example/sec.c -L/app/build/bin -l:tsan-x86_64.a -o test.exe \
#     -fuse-ld=gold \
#     -lm -ldl -lpthread \
#     -z muldefs \
#     -mclwb -mclflushopt \
#     -v


# Compile example
# RUN clang -g -O0 -c -emit-llvm -fPIC -fPIE -I/app/instrumentation/example/ /app/instrumentation/example/test.c /app/instrumentation/example/sec.c

# Disasm the bytecode
# RUN llvm-dis test.bc

# # Run pass on example
# RUN opt -load /app/build/bin/PrdPass.so test.bc sec.bc -enable-new-pm=0 -tsan2 > test_instrumented.bc

# # Disasm the instrumented bytecode
# RUN llvm-dis test_instrumented.bc

# # Compile bytecode to machine code
# RUN llc -asm-verbose=false -O0 -filetype=obj test_instrumented.bc -o test_instrumented.o

# # Link instrumented binary with runtime lib
# RUN clang test_instrumented.o \
#     -o test_instrumented.exe \
#     /app/build/bin/tsan-x86_64.a \
#     -fuse-ld=gold \
#     -lm -ldl -lpthread \
#     -z muldefs \
#     -mclwb -mclflushopt \
#     -v



















# # # Compile pass
# # RUN clang -g3 -shared -o /app/libtsantestpass.so /app/instrumentation/prd/tsanpass.cpp -v -I/usr/include/llvm/ -I/usr/include/llvm-c/ -fPIC


# # # Compile runtime lib



# # # RUN opt-11 -load ./libtsantestpass.so sample.ll -enable-new-pm=0 -S -bsab
# # # RUN opt -load ./libtsantestpass.so sample.ll -enable-new-pm=0 -bsab > a.bc



# # # RUN opt -load ./libtsantestpass.so sample.ll -enable-new-pm=0 -tsan2 > a.bc
# # # RUN llc -asm-verbose=false -O0 -filetype=obj a.bc -o a.o
# # # RUN llvm-dis a.bc



# # # RUN clang a.o -o a.exe
# # # RUN clang a.o -o a.exe src/bin/libclang_rt.tsan_cxx-x86_64.a src/bin/libclang_rt.tsan-x86_64.a
# # # RUN clang a.o -o a.exe src/bin/libclang_rt.tsan_cxx-x86_64.a src/bin/libclang_rt.tsan-x86_64.a -fuse-ld=gold -lm
# #     # -fuse-ld=gold see https://github.com/android/ndk/issues/1088
# #     # -lm because of signgam see https://gcc.gnu.org/legacy-ml/gcc-patches/2013-12/msg00510.html
# # # RUN clang a.o -o a.exe -Lsrc/bin


# # # ENTRYPOINT ["tail", "-f", "/dev/null"]
# # # ENTRYPOINT ["cat", "x.txt", "&&", "/bin/bash"]
# # # ENTRYPOINT ["echo", "x.txt", "&&", "/bin/bash"]
# # # ENTRYPOINT ["/bin/bash"]
# # WORKDIR /app/instrumentation/runtime/compiler-rt
# # RUN cmake .
# # RUN make -j 2




# # WORKDIR /app

# # RUN clang -g -O0 -c -emit-llvm -fPIC -fPIE ./src/example/test.c
# # RUN llvm-dis test.bc

# # RUN opt -load ./libtsantestpass.so test.bc -enable-new-pm=0 -tsan2 > test_instrumented.bc
# # RUN llvm-dis test_instrumented.bc

# # RUN llc -asm-verbose=false -O0 -filetype=obj test_instrumented.bc -o test_instrumented.o

# # RUN clang test_instrumented.o \
# #     -o test_instrumented.exe \
# #     /app/instrumentation/runtime/compiler-rt/lib/linux/libclang_rt.tsan-x86_64.a \
# #     /app/instrumentation/runtime/compiler-rt/lib/linux/libclang_rt.tsan_cxx-x86_64.a \
# #     -fuse-ld=gold \
# #     -lm -ldl -lpthread \
# #     -z muldefs \
# #     -mclwb -mclflushopt \
# #     -v
# #     # src/bin/libclang_rt.tsan_cxx-x86_64.a src/bin/libclang_rt.tsan-x86_64.a \


















# ENTRYPOINT ["cmake", "."]
ENTRYPOINT ["/bin/bash"]
# ENTRYPOINT ["make"]
# CMD /bin/echo "Welcome, $name"

