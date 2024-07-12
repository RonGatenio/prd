#!/bin/bash

set -e

# Get the scripts dir path
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

# Setup env
. $SCRIPTS_DIR/setup-env.sh

SRC_DIR=$SCRIPTS_DIR/../instrumentation

# Create build folder
mkdir $APP_BUILD
mkdir $APP_BIN
mkdir $APP_SHARE

# Build DFSAN abilist
pushd $SRC_DIR/runtime/compiler-rt/lib/dfsan/scripts
dos2unix *.sh
./make_abilist.sh
popd

pushd $APP_BUILD

mkdir pass
pushd pass

cmake $SRC_DIR/pass
make -j

cp $APP_BUILD/pass/prd/PrdPass.so $APP_BIN/
cp $APP_BUILD/pass/dfsan/DFSanPass.so $APP_BIN/

popd

mkdir runtime
pushd runtime

cmake -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ $SRC_DIR/runtime
make -j

cp $APP_BUILD/runtime/compiler-rt/lib/linux/libclang_rt.tsan_cxx-x86_64.a $APP_BIN/
cp $APP_BUILD/runtime/compiler-rt/lib/linux/libclang_rt.tsan-x86_64.a $APP_BIN/
cp $APP_BUILD/runtime/compiler-rt/lib/linux/libclang_rt.dfsan-x86_64.a $APP_BIN/

ar crsT $APP_BIN/cprd-x86_64.a $APP_BIN/libclang_rt.*

popd
