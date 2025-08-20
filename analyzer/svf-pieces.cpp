//===- svf-ex.cpp -- A driver example of SVF-------------------------------------//
//
//                     SVF: Static Value-Flow Analysis
//
// Copyright (C) <2013->  <Yulei Sui>
//

// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.

// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.
//
//===-----------------------------------------------------------------------===//

/*
 // A driver program of SVF including usages of SVF APIs
 //
 // Author: Yulei Sui,
 */

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

#define vContains(v, arg) (std::find(v.begin(), v.end(), arg) != v.end())

static vector<Value *> seen;
#define MAX_DEPTH 10000
void getFunctionfromUse(User * muse, vector<Function *>& users, int depth) {
	if (auto inst = dyn_cast<llvm::Instruction>(muse)) {
			auto func = inst->getFunction();
					if(func)
						users.push_back(func);
					else {
						cout<<"Function not null"<<endl;
					}
	}
	for(auto user: muse->users()) {
		if (vContains(seen, user))
				return;
		if (auto func = dyn_cast<llvm::Function>(user)) {
				if(!vContains(users, func))
						users.push_back(func);
		}
		else if (auto inst = dyn_cast<llvm::Instruction>(user))  {
				auto func = inst->getFunction();
				if(func)
					users.push_back(func);
				else {
					cout<<"Function not null"<<endl;
				}
		}
		else {
				depth++;
				if (depth<MAX_DEPTH && user->hasNUsesOrMore(1))
					getFunctionfromUse(user,users, depth);
				else {
						if (vContains(seen, user) || user->hasNUses(0))
								return;
						seen.push_back(user);
						//Const to Const Data can be ignored, its probably LLVM used
						if (auto type = dyn_cast<llvm::Constant>(user)) {
								int i=0;
								for(auto user1: user->users()){
									if (auto type = dyn_cast<llvm::Constant>(user)) {
										i++;
										(void)type;
									}
									(void)user1;
								}
								if (user->getNumUses () == (unsigned)i) {
										return;
								}
								(void)type;
						}
						cout<<"********************"<<endl;
						cout<<"Depth Expired"<<endl;
						//user->dump();
						cout<<"with "<<user->getNumUses ()<< " users:"<<endl;
						//for(auto user1: user->users()){
						//		user1->dump();
						//}
						cout<<"********************"<<endl;

				}
						
		}
	}
}

void getUseDef(string bitcode, string ddg_out) {
    ofstream debug;
    ofstream ignoreList;
    ignoreList.open("./rtmk.ignore");
    debug.open("./rtmk.log");

    string rtmksec	= "rtmk";
    string shared 	= "shared";
    string pinned 	= "pinned";
    string clone 	= "clone";
    string secret 	= "secret";

	ofstream ddg;
	if (!ddg_out.empty()) {
		ddg.open(ddg_out);
	} else {
		ddg.open("/dev/null");
	}

	ofstream dfmap;
	dfmap.open("out/dfmap");

	LLVMContext context;
	SMDiagnostic err;
	unique_ptr<Module> llvmModule = parseIRFile(bitcode, err, context);
	ddg << "digraph \"dg\" {\nlabel=\"DG\";\n" << endl;
	
	unordered_set<Function *> uniqueFuncs;
	if (llvmModule) {
		for (GlobalVariable &glob : llvmModule->globals()) {
			
			if (glob.getName().str() == "llvm.used" || glob.getName().str() == "_shared_region"
							|| glob.getSection().str().find(rtmksec) != std::string::npos
							|| glob.getSection().str().find(shared) != std::string::npos) {
				ignoreList<<glob.getName().str()<<endl;
				continue;
			}

			if (glob.getSection().str().find(pinned) != std::string::npos) {
				ignoreList<<glob.getName().str()<<endl;
				continue;
			}

			if (glob.getSection().str().find(clone) != std::string::npos) {
				ignoreList<<glob.getName().str()<<endl;
				continue;
			}

			StringRef filename;
			StringRef directory;

			llvm::SmallVector<DIGlobalVariableExpression *, 1> GVs;
			glob.getDebugInfo(GVs);
			for (auto *g: GVs) {
				directory = g->getVariable()->getDirectory();

				dfmap << glob.getName().str() << "##";
				dfmap << g->getVariable()->getFilename().str() << endl;
			}
			std::string fullpath = (directory + "/" + filename).str();
			if (fullpath == "/") fullpath = "";

			ddg << "Node" << (void*)&glob << "[shape=record,type=global,label=" << glob.getName().str() << "];\n";
			vector<Function *> funcs;
			for (User *user : glob.users()) {
				getFunctionfromUse(user, funcs, 0);
			}

			set<Function *> s( funcs.begin(), funcs.end() );
			funcs.assign( s.begin(), s.end() );
			for (auto func: funcs) {
					uniqueFuncs.insert(func);
					ddg << "Node" << &glob << " -> Node" << func << "[style=dashed];\n";
			}
			for (Function *F : uniqueFuncs) { // add node for all functions with format label="{\{fun: main \{ \"file\": \"main.c\" \}\}}"
				ddg << "Node" << F << "[shape=record,type=function,label=" << F->getName().str() << "];\n";
			}
		}
	}
	ddg << "}";
	ddg.close();
	dfmap.close();
}

void getFFMap(string bitcode) {
	LLVMContext context;
	SMDiagnostic err;
	unique_ptr<Module> llvmModule = parseIRFile(bitcode, err, context);

	ofstream ffmap;
	ffmap.open("out/ffmap");
	for (auto &F : *llvmModule) {
		int found = 0;
		for (auto &bb : F) {
			if (found==1)
				break;
			for (auto &stmt : bb) {
				auto &debugInfo = stmt.getDebugLoc();
				if (debugInfo) {
					ffmap << F.getName().str() << "##" << debugInfo->getFilename().str() << endl;
					//fdirmap<<fun->getName().str()<<"##"<<debugInfo->getDirectory().str() <<endl; 
					found =1;
					break;
				}
			}
		}
	}
	ffmap.close();
}

#define OVER_APPOX_TRICK

std::vector<std::string> moduleNameVec;
FlowSensitive *fspta;
SVFIR *svfir;
LLVMModuleSet *llvmModSet;
llvm::Module *ll_mod;

static map<int,vector<string>> compartments;
static map<string, int>compartmentMap;
map<Value *, Function *> function_pointers;
vector<Value *> cloneFuncs;
llvm::cl::opt<std::string> partGuide("p", llvm::cl::desc("<KLEE Compatible bc for taint analysis/symex>"), cl::Optional);

void buildPTA() {
	SVFIRBuilder builder;
	svfir = builder.build();

	fspta = new FlowSensitive(svfir);
	fspta->analyze();

	ll_mod = llvmModSet->getMainLLVMModule();
}

AliasResult aliasQuery(PointerAnalysis* pta, Value* v1, Value* v2){
	SVF::NodeID n1 = SVF::LLVMModuleSet::getLLVMModuleSet()->getValueNode(v1);
	SVF::NodeID n2 = SVF::LLVMModuleSet::getLLVMModuleSet()->getValueNode(v2);
	return pta->alias(n1, n2);
}

bool isFunctionPointer(llvm::Type* type) {
	if (auto *ptrTy = llvm::dyn_cast<llvm::PointerType>(type)) {
        if (!ptrTy->isOpaquePointerTy()) {
            return ptrTy->getNonOpaquePointerElementType()->isFunctionTy();
        }
    }
    return false;  // Not a function pointer
}

string  argToBridge(CallInst * ci, int argnum, Value ** v, Value ** sizeInt) {
	auto arg = ci->getArgOperand(argnum);
	string args;
	auto md = ci->hasFnAttr ("rtmkxcmd");
	(void)md;
	auto fun = ci->getCalledFunction();
	/* If its a normal int we don't need to pass in anything */
	if (arg->getType()->isIntegerTy()) {
			auto intt  = dyn_cast<llvm::IntegerType> (arg->getType());
			if (intt->getBitWidth() <= 32) {
					args = "i";
					llvm::IRBuilder<> Builder(ci);
					auto cast = Builder.CreateIntCast (arg, Type::getInt32Ty(arg->getContext()), false);
					*v = cast;
					*sizeInt = *v;
			} else if (intt->getBitWidth() <= 64) {
					args = "d";
					llvm::IRBuilder<> Builder(ci);
					auto cast = Builder.CreateIntCast (arg, Type::getInt64Ty(arg->getContext()), false);
					*v = cast;
					*sizeInt = *v;
			} else {
					cerr<<"Really Huge Variable is being used!!" <<endl;
					while(1);
			}
	} else if (arg->getType()->isPointerTy()) {
			args = "p";
			llvm::IRBuilder<> Builder(ci);
			if (fun && fun->getAttributes().hasParamAttr (argnum, "rtmkxcmd") ) {
					auto attr = fun->getAttributes().getParamAttr (argnum, "rtmkxcmd");
					auto kw = attr.getValueAsString().str();
					*v = Builder.CreatePointerCast(arg, Type::getInt8PtrTy(arg->getContext()));
					string argkw = "arg";

					if (kw == "opaque") {
							*sizeInt = ConstantInt::get(arg->getContext(),llvm::APInt(32, -1, true));
					} else if (kw == "string") {
							//Get strlen function
							auto func = ll_mod->getFunction("mystrlen");
							if (func==NULL) {
									cerr<< "strlen not implemented" <<endl;
									return 0;
							}
							auto func_type = func->getFunctionType();
							auto f = ll_mod->getOrInsertFunction ("strlen", func_type); //FuncCallee
							//STRLEN Gives you length of string, but we want to get the null terminator too.
							*sizeInt = Builder.CreateAdd(Builder.CreateCall(f, {arg}), ConstantInt::get(arg->getContext(),
													llvm::APInt(32, 1, false))); 
					} else if (kw.find(argkw) != std::string::npos) { 
							kw.erase(kw.find(argkw), argkw.length());
							int argNum = stoi(kw);
							*sizeInt = ci->getArgOperand(argNum);
					} else {
							*sizeInt = ConstantInt::get(arg->getContext(),llvm::APInt(32, 0, true));
					}

			}
			else if (isFunctionPointer(arg->getType())) {
					*v = Builder.CreatePointerCast(arg, Type::getInt8PtrTy(arg->getContext()));
					auto sizeP = Builder.CreateIntToPtr (ConstantInt::get(arg->getContext(),
											llvm::APInt(32, 0, false)), arg->getType());
					auto size = Builder.CreateConstGEP1_32 (NULL, sizeP, 1);
					*sizeInt = ConstantInt::get(arg->getContext(),
									llvm::APInt(32, -1, true));
					(void)size;

			} else 
					if (arg->getType()->isSized()) {
							*v = Builder.CreatePointerCast(arg, Type::getInt8PtrTy(arg->getContext()));
							auto sizeP = Builder.CreateIntToPtr (ConstantInt::get(arg->getContext(),
													llvm::APInt(32, 0, false)), arg->getType());
							PointerType* sizeTy = PointerType::get(sizeP->getType(), 0);
							auto size = Builder.CreateConstGEP1_32 (sizeTy, sizeP, 1);
							*sizeInt = Builder.CreatePtrToInt(size, Type::getInt32Ty(arg->getContext()));
					} else {
							*v = Builder.CreatePointerCast(arg, Type::getInt8PtrTy(arg->getContext()));
							cerr <<"Unsized pointer:";
							//ci->dump();
							*sizeInt  = ConstantInt::get(arg->getContext(),
											llvm::APInt(32, 1, false));
					}
	} else {
			cerr<<"Pass incomplete" <<endl;
			//ci->dump();
			*v = NULL; *sizeInt = NULL;
			args = "";
	}
	return args;
}

string getRetType(CallInst * ci) {
	string ret;
	if (ci->getType()->isVoidTy()) {
			ret = "x";
	} else if (ci->getType()->isIntegerTy()) {
			ret = "i";
	} else if (ci->getType()->isPointerTy()) {
			ret = "p";
	} else {
			cerr<<"Pass incomplete" <<endl;
			//ci->dump();
			ret = "";
	}
	return ret;
}

Type* getRetTy(CallInst * ci, llvm::IRBuilder<> &Builder) {
	llvm::Type * ret;
	if (ci->getType()->isVoidTy()) {
			ret = Builder.getVoidTy();
	} else if (ci->getType()->isIntegerTy()) {
			ret = Builder.getInt32Ty();
	} else if (ci->getType()->isPointerTy()) {
			ret = Builder.getInt8PtrTy();
	} else {
			cerr<<"Pass incomplete" <<endl;
			//ci->dump();
			ret = NULL;
	}
	return ret;
}

int promoteXCallNoCalee(CallInst * ci, BasicBlock::iterator& stmt, int compID);

int promoteXCall(CallInst * ci, Function * callee, BasicBlock::iterator& stmt) {
		//Builder.SetInsertPoint(stmt->getNextNode()->getPrevNode());
		llvm::IRBuilder<> Builder(ci);
		auto num = ci->arg_size();
		(void)num;
		BasicBlock::iterator it(stmt);it--;
		auto fun = ci->getCalledFunction();
		if (fun && fun->getAttributes().getFnAttrs().hasAttribute("rtmkxcmd")) {
				cout<<"Found function with metadata" <<endl;
				auto attr = fun->getAttributes().getFnAttrs().getAttribute("rtmkxcmd");
				auto kw = attr.getValueAsString().str();
				if (kw == "custom_bridge") {
						num = -1;
						cout<<"CUstom Bridge found";
				}
		}

		int compID = compartmentMap[callee->getName().str()];
		promoteXCallNoCalee(ci, stmt, compID);
		return 0;
}
int promoteXCallNoCalee(CallInst * ci, BasicBlock::iterator& stmt, int compID) {
		llvm::IRBuilder<> Builder(ci);
		BasicBlock::iterator it(stmt);it--;
		//Builder.SetInsertPoint(stmt->getNextNode()->getPrevNode());


		auto params = ci->getFunctionType()->params().vec();
		vector<Type *> args;
		vector<Value *> args_val;
		args.push_back(Builder.getInt32Ty());
		args.push_back(Builder.getInt8PtrTy());
		auto p = llvm::ConstantInt::get(Builder.getInt32Ty(), llvm::APInt(32, compID, false));
		args_val.push_back(p);
		auto ccallee = Builder.CreatePointerCast(ci->getCalledOperand(), Builder.getInt8PtrTy());
		args_val.push_back(ccallee);


		int i =0;
		string func_name = getRetType(ci);
		func_name = func_name + "call_arg";
		string suffix = "";
		for (auto arg: params) {
				Value * v;
				Value * size;
				suffix = suffix + argToBridge(ci, i++, &v, &size);
				args.push_back(v->getType());
				args.push_back(size->getType());
				args_val.push_back(v);
				args_val.push_back(size);
				(void)arg;
		}
		func_name = func_name + std::to_string(i) + suffix;

		auto func_type = FunctionType::get(getRetTy(ci, Builder), args, false);
		auto f = ll_mod->getOrInsertFunction(func_name, func_type);
		//		Function* f = Function::Create(func_type, Function::ExternalLinkage, func_name, ll_mod);

		auto new_inst = Builder.CreateCall(f,args_val);
		Instruction * ins;
		if(ci->getType() == new_inst->getType()) {
				ins = new_inst;
		}
		else if (ci->getType()->isPointerTy()) {
				ins = dyn_cast<llvm::Instruction>(Builder.CreatePointerCast(new_inst, ci->getType()));
		}else {
				ins = dyn_cast<llvm::Instruction>(Builder.CreateIntCast(new_inst, ci->getType(),false));
		}

		stmt++;
		ins->removeFromParent();
		//ins->dump();
		ReplaceInstWithInst(ci, ins);

		return 0;
}
int promoteXCallNoCaleeNoId(CallInst * ci, BasicBlock::iterator& stmt) {
		llvm::IRBuilder<> Builder(ci);
		BasicBlock::iterator it(stmt);it--;
		//Builder.SetInsertPoint(stmt->getNextNode()->getPrevNode());

		auto params = ci->getFunctionType()->params().vec();
		vector<Type *> args;
		vector<Value *> args_val;
		args.push_back(Builder.getInt8PtrTy());
		auto ccallee = Builder.CreatePointerCast(ci->getCalledOperand(), Builder.getInt8PtrTy());
		args_val.push_back(ccallee);


		int i =0;
		string func_name = getRetType(ci);
		func_name = func_name + "call_arg";
		string suffix = "_noid";
		for (auto arg: params) {
				Value * v;
				Value * size;
				suffix = suffix + argToBridge(ci, i++, &v, &size);
				args.push_back(v->getType());
				args.push_back(size->getType());
				args_val.push_back(v);
				args_val.push_back(size);
				(void)arg;
		}
		func_name = func_name + std::to_string(i) + suffix;

		auto func_type = FunctionType::get(getRetTy(ci, Builder), args, false);
		auto f = ll_mod->getOrInsertFunction(func_name, func_type);
		//        Function* f = Function::Create(func_type, Function::ExternalLinkage, func_name, ll_mod);

		auto new_inst = Builder.CreateCall(f,args_val);

		Instruction * ins;
		if(ci->getType() == new_inst->getType()) {
				ins = new_inst;
		}
		else if (ci->getType()->isPointerTy()) {
				ins = dyn_cast<llvm::Instruction>(Builder.CreatePointerCast(new_inst, ci->getType()));
		}else {
				ins = dyn_cast<llvm::Instruction>(Builder.CreateIntCast(new_inst, ci->getType(),false));
		}

		stmt++;
		ins->removeFromParent();
		//ins->dump();
		ReplaceInstWithInst(ci, ins);

		return 0;
}

void updateBC() {
	verifyModule(*ll_mod);
	//StringRef file = StringRef("temp.bc");
	std::error_code EC;
	//raw_fd_ostream output = raw_fd_ostream("temp.bc", EC); error: use of deleted function ‘llvm::raw_fd_ostream::raw_fd_ostream(const llvm::raw_fd_ostream&)’
	verifyModule(*ll_mod);
	//Holy Grail of debug
	//ll_mod->dump();
	raw_fd_ostream output("temp.bc", EC);
	llvm::WriteBitcodeToFile(*ll_mod, output);
	cerr<<"temp.bc updated"<<endl;
}

//TODO: clones is not populated with anything, there is probably also other things we use that I haven't put in the needed code for
void instrument(string bitcode) {
		ofstream debug;
		ofstream ignoreList;
		ignoreList.open("./rtmk.ignore");
		debug.open("./rtmk.log");
		string rtmksec= "rtmk";
		string shared = "shared";
		string pinned = "pinned";
		string clone = "clone";
		string secret = "secret";

		vector<Value *> clones; //We need to track our clones so we don't instrument them.

		string line;
		ifstream cmap("./compartmentMap");
		while (getline(cmap, line)) {
			istringstream iss(line);
			string key, value;

			if (getline(iss, key, '\t') && getline(iss, value)) {
				compartmentMap[key] = stoi
				(value);
			}
		}

		int directCalls = 0;
		int indirectCalls = 0;

		/* TODO: Assign pinned resources their own compartments based on data or code */

		/* Instrument code for interprocess calls */
		//for (SVFModule::llvm_iterator F = svfModule->llvmFunBegin(), E = svfModule->llvmFunEnd(); F != E; ++F) {
		for (llvm::Function &F : *ll_mod) {
				string rtmksec= "rtmk";
				if (F.getSection().str().find(rtmksec) != std::string::npos) {
						continue;
				}
				string init= "init";
				if (F.getSection().str().find(init) != std::string::npos) {
						continue;
				}
				string shared = "shared_func";
				if (F.getSection().str().find(shared) != std::string::npos) {
						continue;
				}

				for (auto bb=F.begin();bb!=F.end();bb++) {
						for (auto stmt =bb->begin();stmt!=bb->end(); stmt++) {
								auto callerID  = compartmentMap[F.getName().str()];
								if (auto ci= dyn_cast<llvm::CallInst> (stmt)) {
										if (ci->isInlineAsm ()) continue; /* TODO: Currently we don't cater to inline asm */
										auto callee = ci->getCalledFunction ();
										if (callee) {
												string rtmksec= "rtmk";
												if (callee->getSection().str().find(rtmksec) != std::string::npos) {
														cout<<"Skipping call because its to rtmk"<<endl;
														continue;
												}
												auto calleeID = compartmentMap[callee->getName().str()];
												/* See if this is a cross call */
												if (callerID == calleeID)
														continue;
												//TODO: Inconsistency between compartmentMap and actual compartment due to cloning
												if (vContains(clones, callee) || vContains(cloneFuncs, callee)) {
														continue;
												}
												/* See if this is a debug call/intrinsic */
												string llvm = "llvm";
												if (callee->getName().str().find(llvm) != std::string::npos) continue;
												llvm::IRBuilder<> Builder(stmt->getParent());
												BasicBlock::iterator it(stmt);it--;
												//Builder.SetInsertPoint(stmt->getNextNode()->getPrevNode());
												directCalls++;
												promoteXCall(ci, callee, stmt);
										}
										else {
												/* Indirect calls */
												cerr<<"Indirect Call"<<endl;
												vector<Function *> targets;
												auto called = ci->getCalledOperand();
												//called->dump();
												auto ptr = called;
												if (auto li= dyn_cast<llvm::LoadInst>(called)) {
														ptr= li->getPointerOperand();
												}
												{
														cout<<"An alias pointer used"<<endl;
														ptr = called;
														//ptr->dump();
														for(auto &pts: function_pointers) {
																//cerr<<"Comparing with:"; pts.first->dump();
																if (aliasQuery(fspta, ptr, pts.first)) {
																		cerr<<"Target Found:";
																		cerr<<pts.second->getName().str()<<endl;
																		targets.push_back(pts.second);
																}
														}
														set<Function *> s( targets.begin(), targets.end() );
														targets.assign( s.begin(), s.end() );
														/* See if all targets are within the same compartment?? */
														callerID = compartmentMap[F.getName().str()];
														map<int, int> calledComp;
														int onlyTargetCache = 0;
														for (auto &t: targets) {
																calledComp[compartmentMap[t->getName().str()]] = 1;
																onlyTargetCache = compartmentMap[t->getName().str()];
														}

														if (calledComp.size() == 0) {
																/* Could not determine anything */
																cerr<<"Zero Target"<<endl;
																indirectCalls++;
																promoteXCallNoCaleeNoId(ci, stmt);
														}
														else if (calledComp.size() == 1) {
																/* Instrument function for direct call */
																cerr<<"Only1 targets"<<endl;
																if (onlyTargetCache != callerID) {
																		indirectCalls++;
																		promoteXCallNoCalee(ci, stmt, onlyTargetCache);
																}

														} else {
																/* Instrument call so that runtime figures the required compartment */
																cerr<<"Multiple target"<<endl; //Specialize
																indirectCalls++;
																promoteXCallNoCaleeNoId(ci,stmt);
														}
												}

										}
								}
						}
				}
		}

		ofstream xcalls;
		xcalls.open("./rtmk.xcall");
		xcalls << "Direct xcalls:		" << directCalls << endl;
		xcalls << "Indirect xcalls:		" << indirectCalls << endl;
		//for (int i =0; i < compartmentID; i++) {
		//		xcalls<<"Compartment #:"<<i<<endl;
		//		xcalls<<"Direct xcalls:			"<<directCall[i]<<endl;
		//		xcalls<<"Indirect xcalls:		"<<indirectCall[i]<<endl;
		//}

		//ofstream serializedD;
		//ofstream serializedI;
		//serializedD.open("./rtmk.xcalld");
		//serializedI.open("./rtmk.xcalli");
		//for(int i =0; i< compartmentID; i++) {
		//		serializedD<<directCall[i]<<endl;
		//		serializedI<<indirectCall[i]<<endl;
		//}


		updateBC();
}

int main(int argc, char ** argv)
{
	string bitcode;
	string ddg_out;

	bool _use_def 		= false;
	bool _ffmap 		= false;
	bool _instrument 	= false;

	for (int i = 1; i < argc; i++) {
		string arg(argv[i]);
		if (arg.rfind("bc=", 0) == 0) {
			bitcode = arg.substr(3);
		} else if (arg.rfind("ddg=", 0) == 0) {
			ddg_out = arg.substr(4);
		} else if (arg == "-use-def") {
			_use_def = true;
		} else if (arg == "-ffmap") {
			_ffmap = true;
		} else if (arg == "-instrument") {
			_instrument = true;
		}
	}

    if (_use_def && !bitcode.empty()) {
		getUseDef(bitcode, ddg_out);
    }
	if (_ffmap && !bitcode.empty()) {
		getFFMap(bitcode);
	}
	if (_instrument && !bitcode.empty()) {
		moduleNameVec.push_back(bitcode);

		llvmModSet = LLVMModuleSet::getLLVMModuleSet();
		llvmModSet->buildSVFModule(moduleNameVec);

		buildPTA();
		instrument(bitcode);
	}

    return 0;
}
 