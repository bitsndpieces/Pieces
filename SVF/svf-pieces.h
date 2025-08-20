#ifndef SVF_PIECES_H
#define SVF_PIECES_H

#include "AE/Core/AbstractState.h"
#include "Graphs/SVFG.h"
#include "SVF-LLVM/LLVMUtil.h"
#include "SVF-LLVM/SVFIRBuilder.h"
#include "SVF-LLVM/LLVMModule.h"
#include "SVFIR/SVFIR.h"
#include "Util/CommandLine.h"
#include "Util/Options.h"
#include "WPA/Andersen.h"
#include "WPA/FlowSensitive.h"

#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include "llvm/IR/Verifier.h"
#include "llvm/IR/Function.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/ADT/StringRef.h"

#include <fstream>
#include <sstream>

using namespace llvm;
using namespace std;
using namespace SVF;

#define FREERTOS
#define OVER_APPOX_TRICK
#define MAX_DEPTH 10000

#define vContains(v, arg) (std::find(v.begin(), v.end(), arg) != v.end())

//instrument.cpp
void instrument(string bitcode);

// threads.cpp
void getThreads();

#endif