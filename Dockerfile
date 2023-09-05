# LLVM version

# Use an LLVM Docker image as the base image
# FROM silkeh/clang:$LLVM_VERSION
FROM silkeh/clang:latest

ENV LLVM_VERSION 16
# Set the LLVM installation directory (adjust the path as needed)
ENV LLVM_HOME /usr/lib/llvm-$LLVM_VERSION

# Set the LLVM CMake directory
ENV LLVM_CMAKE_DIR $LLVM_HOME/lib/cmake/llvm

# Add LLVM bin directory to the PATH
ENV PATH $LLVM_HOME/bin:$PATH

# Add LLVM lib directory to LD_LIBRARY_PATH (optional)
ENV LD_LIBRARY_PATH $LLVM_HOME/lib:$LD_LIBRARY_PATH

# Add LLVM include directory to C_INCLUDE_PATH and CPLUS_INCLUDE_PATH (optional)
ENV C_INCLUDE_PATH $LLVM_HOME/include:$C_INCLUDE_PATH
ENV CPLUS_INCLUDE_PATH $LLVM_HOME/include:$CPLUS_INCLUDE_PATH

# Set LLVM_DIR for CMake projects (optional)
ENV LLVM_DIR $LLVM_CMAKE_DIR

# Install necessary packages
RUN apt-get update && \
    apt-get install -y cmake build-essential zlib1g-dev

# Create a working directory
WORKDIR /app

# # Create a directory in the container to copy your folder into
# RUN mkdir /app

# Copy your "src" folder and CMakeLists.txt to the container
COPY CMakeLists.txt /app/
ADD src /app/src

# Create a build directory and run CMake
RUN (mkdir build && cd build && cmake -DENABLE_LLVM_SHARED=1 ..)

# Build your LLVM pass
RUN cmake --build build

# Install the LLVM pass
# RUN cp /app/build/PRD.so /path/to/llvm/lib/

# Clean up the build files if needed
# RUN rm -rf /app/build

# # Copy the LLVM pass source code to the container
# COPY src/ /app

# # Compile the LLVM pass
# RUN clang++ -shared -o /app/<YourPassName>.so -I/usr/local/include/llvm-c -I/usr/local/include/llvm-cxx /app/<YourPassName>.cpp

# Create a sample LLVM IR file (you can replace this with your own)
RUN echo "define i32 @main() {" > /app/sample.ll && \
    echo "  ret i32 0" >> /app/sample.ll && \
    echo "}" >> /app/sample.ll

# Run your LLVM pass on the sample LLVM IR file
RUN opt -load /app/build/libPRD.so -S /app/sample.ll -o /app/output.ll && cat /app/output.ll -DENABLE_LLVM_SHARED=1
# CMD opt -load /app/build/libPRD.so -c -S /app/sample.ll -o /app/output.ll && cat /app/output.ll
# CMD opt -load /app/build/libPRD.so -S /app/sample.ll -o /app/output.ll && cat /app/output.ll
# CMD /bin/bash
ENTRYPOINT ["tail", "-f", "/dev/null"]