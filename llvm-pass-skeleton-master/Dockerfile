FROM ubuntu:latest

# Set LLVM version
ENV LLVM_VERSION 14

# Install dev packages
RUN apt-get update && apt-get install -y llvm-${LLVM_VERSION} llvm-${LLVM_VERSION}-dev clang-${LLVM_VERSION}
RUN apt install -y cmake

# Install tools packages
RUN apt install -y mlocate less

# Set env
ENV PATH /usr/lib/llvm-${LLVM_VERSION}/bin:$PATH

RUN ln -s /usr/include/llvm-${LLVM_VERSION} /usr/include/llvm
RUN ln -s /usr/include/llvm-c-${LLVM_VERSION} /usr/include/llvm-c

RUN echo . /app/src/scripts/setup-env.sh >> ~/.bashrc

# Create a working directory
WORKDIR /app

# Copy src folder to docker
COPY src /app/src

RUN /app/src/scripts/build.sh

# Compile example
# RUN clang -g -O0 -c -emit-llvm -fPIC -fPIE /app/src/example/test.c

# Disasm the bytecode
# RUN llvm-dis test.bc

# # Run pass on example

RUN clang -O0 -g -c -emit-llvm -fpass-plugin=/app/build/bin/SkeletonPass.so /app/src/example/test.c
RUN clang++ test.bc -L/app/build/bin -lRuntimeLib -o test.exe
# note that test.bc must come before -lRuntimeLib because https://stackoverflow.com/questions/41364698/c-differ-between-linking-with-o-and-with-a-file-different-behavior-why

# OR

RUN clang -O0 -g -fpass-plugin=/app/build/bin/SkeletonPass.so /app/src/example/test.c -L/app/build/bin -lRuntimeLib -o test.exe -lstdc++


ENTRYPOINT ["/bin/bash"]
