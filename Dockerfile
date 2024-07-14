#####################################################################
# Setup stage
#####################################################################

FROM ubuntu:22.04 AS setup

ARG DEBIAN_FRONTEND=noninteractive

# Set LLVM version
ENV LLVM_VERSION=14

# Install dev packages
RUN apt update
RUN apt install -y llvm-${LLVM_VERSION} llvm-${LLVM_VERSION}-dev clang-${LLVM_VERSION}
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

# Install tini for the startup script
RUN apt install -y tini

# Set llvm env
ENV PATH=/usr/lib/llvm-${LLVM_VERSION}/bin:$PATH

RUN ln -s /usr/include/llvm-${LLVM_VERSION} /usr/include/llvm
RUN ln -s /usr/include/llvm-c-${LLVM_VERSION} /usr/include/llvm-c


#####################################################################
# Build Cprd stage
#####################################################################

FROM setup AS build-cprd

# Copy instrumentation folder to container
COPY instrumentation /app/instrumentation
COPY scripts /app/scripts

# Setup scripts
WORKDIR /app/scripts
RUN dos2unix *.sh

# Build pass and runtime lib
RUN ./build.sh


#####################################################################
# Build PyCprd stage
#####################################################################

FROM setup AS build-pycprd

# Copy pyprd folder to container
COPY pyprd /app/pyprd

# Install pyprd
WORKDIR /app/pyprd
RUN python3 -m pip install -r requirements.txt
RUN python3 setup.py install


#####################################################################
# Tool Ready stage
#####################################################################

FROM setup AS cprd

# Copy cprd
COPY --from=build-cprd /app/scripts /app/scripts
COPY --from=build-cprd /app/build /app/build

# Copy pycprd
COPY --from=build-pycprd /usr/local /usr/local

# Setup env
WORKDIR /app/scripts
RUN ./setup-env.sh
RUN cat ./setup-env.sh >> ~/.bashrc

# Set workdir
WORKDIR /app

# Use tini as the entry point
ENTRYPOINT ["/usr/bin/tini", "--", "/app/scripts/entrypoint.sh"]


#####################################################################
# Benchmarks stage
#####################################################################

FROM cprd AS benchmarks

# Copy benchmarks folder
COPY benchmarks /app/benchmarks

# Setup benchmarks
WORKDIR /app/benchmarks

# ENTRYPOINT [ "/app/instrumentation/scripts/setup-env.sh" ]
# CMD [ "/bin/bash", "-c", "/app/benchmarks/run.sh; /bin/bash" ]
# ENTRYPOINT [ "/bin/bash" ]

WORKDIR /app/benchmarks/benchmark-runner

# Set the entry point to run the benchmarks
# ENTRYPOINT ["/bin/bash", "-c"]

# Set the default command to run the Python script and then start a bash shell
# CMD ["if [ -z \"$@\" ]; then python3 benchmark_runner.py FAST_FAIR; fi; exec \"$@\""]
# ENTRYPOINT ["/usr/bin/tini", "--", "/app/scripts/entrypoint.sh"]

# CMD ["python3", "benchmark_runner.py", "list"]
# CMD ["python3", "benchmark_runner.py", "FAST_FAIR"]
RUN dos2unix *.sh
CMD ["./benchmarks.sh"]
# CMD python3 benchmark_runner.py FAST_FAIR
# CMD [ "/bin/bash", "-c", "python3 benchmark_runner.py FAST_FAIR; /bin/bash" ]
# CMD [ "/bin/bash" ]

# ENTRYPOINT ["/bin/bash"]


