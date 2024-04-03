#!/bin/bash

set -e

# Get the scripts dir path
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

# Setup env
. $SCRIPTS_DIR/setup-env.sh

SRC_DIR=$SCRIPTS_DIR/..

# Create build folder
mkdir $APP_BUILD
mkdir $APP_BIN
mkdir $APP_SHARE

pushd $APP_BUILD

cmake $SRC_DIR
make -j

cp $APP_BUILD/pass/prd/PrdPass.so $APP_BIN/
cp $APP_BUILD/runtime/compiler-rt/lib/linux/libclang_rt.tsan_cxx-x86_64.a $APP_BIN/
cp $APP_BUILD/runtime/compiler-rt/lib/linux/libclang_rt.tsan-x86_64.a $APP_BIN/
cp $APP_BUILD/runtime/compiler-rt/lib/linux/libclang_rt.dfsan-x86_64.a $APP_BIN/

ar crsT $APP_BIN/cprd-x86_64.a $APP_BIN/libclang_rt.*
