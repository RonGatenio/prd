@echo off

@REM docker build -t llvm-pass-container . && start /b docker run llvm-pass-container
docker build -t skeleton-pass-container . && docker run -it skeleton-pass-container

