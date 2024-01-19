FROM ubuntu:latest

# Set LLVM version
ENV LLVM_VERSION 11

# Install dev packages
RUN apt-get update && apt-get install -y llvm-${LLVM_VERSION} llvm-${LLVM_VERSION}-dev clang-${LLVM_VERSION}

# Install tools packages
RUN apt install -y cmake
RUN apt install -y mlocate less

# Set env
ENV PATH /usr/lib/llvm-${LLVM_VERSION}/bin:$PATH

RUN ln -s /usr/include/llvm-${LLVM_VERSION} /usr/include/llvm
RUN ln -s /usr/include/llvm-c-${LLVM_VERSION} /usr/include/llvm-c

RUN printf "export LLVM_INSTALL_PREFIX=\$(llvm-config --prefix)\n"     >> ~/.bashrc
RUN printf "export LLVM_DEFINITIONS=\$(llvm-config --cxxflags)\n"      >> ~/.bashrc
RUN printf "export LLVM_INCLUDE_DIRS=\$(llvm-config --includedir)\n"   >> ~/.bashrc
RUN printf "export LLVM_LIBRARY_DIRS=\$(llvm-config --libdir)\n"       >> ~/.bashrc
RUN printf "export LLVM_CMAKE_DIR=\$(llvm-config --cmakedir)\n"        >> ~/.bashrc

# Create a working directory
WORKDIR /app

# Copy src folder to docker
COPY src /app/src

# Compile pass
RUN clang -g3 -shared -o /app/libtsantestpass.so /app/src/prd/tsanpass.cpp -v -I/usr/include/llvm/ -I/usr/include/llvm-c/ -fPIC

# Generate sample
RUN echo "define i32 @main() {" > /app/sample.ll && \
    echo "  ret i32 0" >> /app/sample.ll && \
    echo "}" >> /app/sample.ll


# RUN opt -load ./libdummypass.so -myprd sample.ll -enable-new-pm=0 -S 2> x.txt
# CMD ["opt -load ./libdummypass.so -myprd sample.ll -enable-new-pm=0"]

# RUN opt -load ./libtsantestpass.so -tsan sample.ll -enable-new-pm=0 -S 2> x.txt
# RUN opt-11 -load ./libtsantestpass.so --print-passes


# Compile runtime lib



# RUN opt-11 -load ./libtsantestpass.so sample.ll -enable-new-pm=0 -S -bsab
# RUN opt -load ./libtsantestpass.so sample.ll -enable-new-pm=0 -bsab > a.bc



# RUN opt -load ./libtsantestpass.so sample.ll -enable-new-pm=0 -tsan2 > a.bc
# RUN llc -asm-verbose=false -O0 -filetype=obj a.bc -o a.o
# RUN llvm-dis a.bc



# RUN clang a.o -o a.exe
# RUN clang a.o -o a.exe src/bin/libclang_rt.tsan_cxx-x86_64.a src/bin/libclang_rt.tsan-x86_64.a
# RUN clang a.o -o a.exe src/bin/libclang_rt.tsan_cxx-x86_64.a src/bin/libclang_rt.tsan-x86_64.a -fuse-ld=gold -lm
    # -fuse-ld=gold see https://github.com/android/ndk/issues/1088
    # -lm because of signgam see https://gcc.gnu.org/legacy-ml/gcc-patches/2013-12/msg00510.html
# RUN clang a.o -o a.exe -Lsrc/bin


# ENTRYPOINT ["tail", "-f", "/dev/null"]
# ENTRYPOINT ["cat", "x.txt", "&&", "/bin/bash"]
# ENTRYPOINT ["echo", "x.txt", "&&", "/bin/bash"]
# ENTRYPOINT ["/bin/bash"]
WORKDIR /app/src/runtime/compiler-rt
RUN cmake .
RUN make -j 2




WORKDIR /app

RUN clang++ -g -O0 -c -emit-llvm -fPIC -fPIE ./src/example/test.cpp
RUN llvm-dis test.bc

RUN opt -load ./libtsantestpass.so test.bc -enable-new-pm=0 -tsan2 > test_instrumented.bc
RUN llvm-dis test_instrumented.bc

RUN llc -asm-verbose=false -O0 -filetype=obj test_instrumented.bc -o test_instrumented.o

RUN clang++ test_instrumented.o \
    -o test_instrumented.exe \
    src/bin/libclang_rt.tsan_cxx-x86_64.a src/bin/libclang_rt.tsan-x86_64.a \
    -fuse-ld=gold \
    -lm -ldl -lpthread \
    -z muldefs \
    -mclwb -mclflushopt \
    -v


















# ENTRYPOINT ["cmake", "."]
ENTRYPOINT ["/bin/bash"]
# ENTRYPOINT ["make"]
# CMD /bin/echo "Welcome, $name"

