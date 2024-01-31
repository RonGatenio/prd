#!/bin/bash

set -eux

# Get the scripts dir path
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

# Setup env
. $SCRIPTS_DIR/setup-env.sh

SRC_DIR=$SCRIPTS_DIR/..
ROOT_DIR=$SRC_DIR/..
BUILD_DIR=$ROOT_DIR/build
BIN_DIR=$BUILD_DIR/bin

# Create build folder
mkdir $BUILD_DIR
mkdir $BIN_DIR

pushd $BUILD_DIR

cmake $SRC_DIR
make -j 4

mv $BUILD_DIR/*/*.so $BIN_DIR/
mv $BUILD_DIR/*/*.a $BIN_DIR/
