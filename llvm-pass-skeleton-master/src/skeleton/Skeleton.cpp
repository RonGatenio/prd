#include "llvm/Pass.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/ADT/MapVector.h"
#include "llvm/IR/Instruction.h"

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
        auto &OpcodeMap = AM.getResult<OpcodeCounter>(M);

        for (auto &F : M) {
            errs() << "I saw a function called " << F.getName() << "!\n";
            for (auto &BB : F)
            {
                for (auto &I : BB)
                {
                    errs() << "    I saw opcode " << OpcodeMap[&I] << "\n";
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
