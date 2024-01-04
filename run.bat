@echo off

@REM docker build -t llvm-pass-container . && start /b docker run llvm-pass-container
docker build -t llvm-pass-container . && docker run -it llvm-pass-container

