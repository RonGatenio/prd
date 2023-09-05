#include "llvm/Pass.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"

using namespace llvm;

namespace {
  struct MyPass : public ModulePass {
    static char ID;
    MyPass() : ModulePass(ID) {}

    bool runOnModule(Module &M) override {
      // Iterate through functions and instructions to trace program execution.
      for (Function &F : M) {
        for (BasicBlock &BB : F) {
          for (Instruction &I : BB) {
            // Trace the instruction here.
          }
        }
      }
      return false; // This pass doesn't modify the module.
    }
  };
}

char MyPass::ID = 0;
static RegisterPass<MyPass> X("myprd", "My Custom LLVM Pass", false, false);
