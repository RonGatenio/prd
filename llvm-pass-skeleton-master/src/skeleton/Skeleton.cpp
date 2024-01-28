#include "llvm/Pass.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/ADT/MapVector.h"
#include "llvm/IR/Instruction.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Type.h"

using namespace llvm;

namespace {

using ResultOpcodeCounter = llvm::MapVector<llvm::Instruction*, unsigned>;

struct OpcodeCounter : public llvm::AnalysisInfoMixin<OpcodeCounter> {
  using Result = ResultOpcodeCounter;
  Result run(llvm::Module &M, llvm::ModuleAnalysisManager &);
//   Result run(llvm::Function &F, llvm::FunctionAnalysisManager &);

  OpcodeCounter::Result generateOpcodeMap(llvm::Module &M);
//   OpcodeCounter::Result generateOpcodeMap(llvm::Function &F);
  // Part of the official API:
  //  https://llvm.org/docs/WritingAnLLVMNewPMPass.html#required-passes
  static bool isRequired() { return true; }

private:
  // A special type used by analysis passes to provide an address that
  // identifies that particular analysis pass type.
  static llvm::AnalysisKey Key;
  friend struct llvm::AnalysisInfoMixin<OpcodeCounter>;
};

llvm::AnalysisKey OpcodeCounter::Key;

OpcodeCounter::Result OpcodeCounter::generateOpcodeMap(llvm::Module &M) {
  OpcodeCounter::Result OpcodeMap;

  unsigned counter = 0;

  for (auto &Func : M) {
    for (auto &BB : Func) {
        for (auto &Inst : BB) {
            OpcodeMap[&Inst] = counter++;
            // StringRef Name = Inst.getOpcodeName();

            // if (OpcodeMap.find(Name) == OpcodeMap.end()) {
            //     OpcodeMap[Inst.getOpcodeName()] = 1;
            // } else {
            //     OpcodeMap[Inst.getOpcodeName()]++;
            // }
        }
    }
  }

  return OpcodeMap;
}

OpcodeCounter::Result OpcodeCounter::run(llvm::Module &M,
                                         llvm::ModuleAnalysisManager &) {
  return generateOpcodeMap(M);
}

struct SkeletonPass : public PassInfoMixin<SkeletonPass> {
    PreservedAnalyses run(Module &M, ModuleAnalysisManager &AM) {

        // Get a reference to the LLVM context.
        LLVMContext &Context = M.getContext();

        // Create an IRBuilder for constructing new instructions.
        IRBuilder<> Builder(Context);

        FunctionCallee InstructionLogFunc = M.getOrInsertFunction(
            // "_Z15log_instructionj", // Name of the new function.
            "log_instruction", // Name of the new function.
            Type::getVoidTy(Context), // Return type.
            Type::getInt32Ty(Context)
        );

        

    //     CallInst *NewCall = Builder.CreateCall(NewFunction, {});



        auto &OpcodeMap = AM.getResult<OpcodeCounter>(M);

        for (auto &F : M) {
            errs() << "I saw a function called " << F.getName() << "!\n";
            for (auto &BB : F)
            {
                errs() << "  I saw a BB in function called " << F.getName() << "!\n";
                // Iterate through the instructions of the basic block
                for (Instruction &I : BB) {
                    errs() << "    I saw opcode " << OpcodeMap[&I] << " in function called " << F.getName() << "!\n";

                    // Check if the instruction is a load instruction
                    if (LoadInst *loadInst = dyn_cast<LoadInst>(&I)) {
                        errs() << "      I a load instruction\n";
                        
                        // Create an unsigned int constant (replace 42 with the actual value)
                        ConstantInt *argValue = ConstantInt::get(Type::getInt32Ty(Context), OpcodeMap[&I]);

                        // Insert the call instruction before the load instruction
                        CallInst::Create(InstructionLogFunc, {argValue}, "", loadInst);
                    }
                }
            }
        }
        return PreservedAnalyses::all();
    };
};

}

extern "C" LLVM_ATTRIBUTE_WEAK ::llvm::PassPluginLibraryInfo
llvmGetPassPluginInfo() {
    errs() << "WHATTT!\n";
    return {
        .APIVersion = LLVM_PLUGIN_API_VERSION,
        .PluginName = "SkeletonPass",
        .PluginVersion = LLVM_VERSION_STRING,
        .RegisterPassBuilderCallbacks = [](PassBuilder &PB) {
            // PB.registerPipelineParsingCallback(
            //     [](StringRef Name, ModulePassManager &MPM,
            //        ArrayRef<PassBuilder::PipelineElement>) {
            //     //   if (Name == "skeleton-pass") {
            //         MPM.addPass(SkeletonPass());
            //         return true;
            //     //   }
            //       return false;
            //     });
            // PB.registerPipelineStartEPCallback(
            //     [](ModulePassManager &MPM) {
            //         MPM.addPass(SkeletonPass());
            //     });
            // PB.registerAnalysisRegistrationCallback
            PB.registerPipelineEarlySimplificationEPCallback(
                [](ModulePassManager &MPM, auto) {
                    MPM.addPass(SkeletonPass());
                    return true;
            });

            PB.registerAnalysisRegistrationCallback(
                // [](FunctionAnalysisManager &FAM) {
                [](ModuleAnalysisManager &MAM) {
                    MAM.registerPass([&] { return OpcodeCounter(); });
                });
        }
    };
}
