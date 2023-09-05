#include "llvm/Pass.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/IRBuilder.h"

using namespace llvm;

namespace {
  struct MyFunctionReplacementPass : public FunctionPass {
    static char ID;
    MyFunctionReplacementPass() : FunctionPass(ID) {}

    bool runOnFunction(Function &F) override {
      // Get a reference to the LLVM context.
      LLVMContext &Context = F.getContext();

      // Create an IRBuilder for constructing new instructions.
      IRBuilder<> Builder(Context);

      // Define the function to replace (you can change this to match your function).
      FunctionCallee OldFunction = F.getParent()->getOrInsertFunction(
          "old_function", // Name of the function to replace.
          Type::getVoidTy(Context) // Return type.
      );

      // Define the new function to call (you can change this to match your new function).
      FunctionCallee NewFunction = F.getParent()->getOrInsertFunction(
          "new_function", // Name of the new function.
          Type::getVoidTy(Context) // Return type.
      );

      // Iterate through basic blocks and instructions in the function.
      for (BasicBlock &BB : F) {
        for (Instruction &I : BB) {
          // Check if the instruction is a call instruction.
          if (CallInst *CI = dyn_cast<CallInst>(&I)) {
            // Check if the called function is the function to replace.
            if (CI->getCalledFunction() == OldFunction.getCallee()) {
              // Create a new call instruction to the new function.
              CallInst *NewCall = Builder.CreateCall(NewFunction, {});
              
              // Replace the old call instruction with the new one.
              CI->replaceAllUsesWith(NewCall);
              CI->eraseFromParent();
            }
          }
        }
      }

      return true; // The function was modified.
    }
  };
}

char MyFunctionReplacementPass::ID = 0;
static RegisterPass<MyFunctionReplacementPass> X("myprd", "Replace function calls", false, false);
