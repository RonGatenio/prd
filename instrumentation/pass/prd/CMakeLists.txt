add_llvm_pass_plugin(PrdPass
    Prd.cpp
    tsanpass.cpp
    ../dfsan/DataFlowSanitizer.cpp
)
