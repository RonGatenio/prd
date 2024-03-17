//===- Transforms/Instrumentation/ThreadSanitizer.h - TSan Pass -----------===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
//
// This file defines the thread sanitizer pass.
//
//===----------------------------------------------------------------------===//

#ifndef PRD_TSANPASS_H
#define PRD_TSANPASS_H

#include "llvm/IR/PassManager.h"
#include "llvm/Pass.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"

namespace llvm {
// Insert ThreadSanitizer (race detection) instrumentation
FunctionPass *createThreadSanitizerLegacyPassPass();

/// A function pass for tsan instrumentation.
///
/// Instruments functions to detect race conditions reads. This function pass
/// inserts calls to runtime library functions. If the functions aren't declared
/// yet, the pass inserts the declarations. Otherwise the existing globals are
struct PrdFunctionPass : public PassInfoMixin<PrdFunctionPass> {
  PreservedAnalyses run(Function &F, FunctionAnalysisManager &FAM);
  static bool isRequired() { return true; }
};

/// A module pass for tsan instrumentation.
///
/// Create ctor and init functions.
struct PrdModulePass : public PassInfoMixin<PrdModulePass> {
  PreservedAnalyses run(Module &M, ModuleAnalysisManager &MAM);
  static bool isRequired() { return true; }
};

} // namespace llvm
#endif /* PRD_TSANPASS_H */
