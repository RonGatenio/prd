@echo off

docker build -t llvm-pass-container . && docker run llvm-pass-container

