#!/bin/bash

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
DFSAN_DIR=$SCRIPTS_DIR/..
ABILISTS_DIR=$DFSAN_DIR/abilists

OUTPUT=$APP_SHARE/dfsan_abilist.txt

cat ${ABILISTS_DIR}/*.txt > $OUTPUT

python3 ${SCRIPTS_DIR}/build-libc-list.py --with-libstdcxx >> $OUTPUT
