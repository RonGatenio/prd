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

# Install gdb for debugging
RUN apt install -y gdb

# Set llvm env
ENV PATH /usr/lib/llvm-${LLVM_VERSION}/bin:$PATH

RUN ln -s /usr/include/llvm-${LLVM_VERSION} /usr/include/llvm
RUN ln -s /usr/include/llvm-c-${LLVM_VERSION} /usr/include/llvm-c


#####################################################################
# Build stage
#####################################################################

FROM setup AS build

# Create a working directory
WORKDIR /app

# Copy instrumentation folder to container
COPY instrumentation /app/instrumentation

# Setup scripts
WORKDIR /app/instrumentation/scripts
RUN dos2unix *.sh

# Setup env
RUN ./setup-env.sh
RUN cat /app/instrumentation/scripts/setup-env.sh >> ~/.bashrc

# Build pass and runtime lib
RUN ./build.sh

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

# Setup benchmarks
WORKDIR /app/benchmarks
RUN dos2unix *.sh
RUN ./run.sh

ENTRYPOINT ["/bin/bash"]
