add_llvm_pass_plugin(PrdPass
    Prd.cpp
    tsanpass.cpp
    DataFlowSanitizer.cpp
)

add_definitions(-DAPP_SHARE="$ENV{APP_SHARE}")
