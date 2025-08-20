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

#include "svf-pieces.h"

std::vector<std::string> moduleNameVec;

FlowSensitive *fspta;
SVFIR *svfir;
LLVMModuleSet *llvmModSet;

llvm::Module *ll_mod;
//llvm::cl::opt<std::string> partGuide("p", llvm::cl::desc("<KLEE Compatible bc for taint analysis/symex>"), cl::Optional);

static vector<Value *> seen;
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

	ddg << "digraph \"dg\" {\nlabel=\"DG\";\n" << endl;
	
	unordered_set<Function *> uniqueFuncs;
	for (GlobalVariable &glob : ll_mod->globals()) {
		
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
	ddg << "}";
	ddg.close();
	dfmap.close();
}

void getFFMap(string bitcode) {
	ofstream ffmap;
	ffmap.open("out/ffmap");
	for (auto &F : *ll_mod) {
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


void buildPTA() {
	SVFIRBuilder builder;
	svfir = builder.build();

	fspta = new FlowSensitive(svfir);
	fspta->analyze();
}

int main(int argc, char ** argv)
{
	string bitcode;
	string ddg_out;

	bool _use_def 		= false;
	bool _ffmap 		= false;
	bool _get_threads	= false;
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
		} else if (arg == "-get-threads") {
			_get_threads = true;
		} else if (arg == "-instrument") {
			_instrument = true;
		}
	}

	if (bitcode.empty()) {
		errs() << "You must provide a bitcode file\n";
		return 1;
	}

	moduleNameVec.push_back(bitcode);

	llvmModSet = LLVMModuleSet::getLLVMModuleSet();
	llvmModSet->buildSVFModule(moduleNameVec);

	ll_mod = llvmModSet->getMainLLVMModule();

	buildPTA();

    if (_use_def) {
		getUseDef(bitcode, ddg_out);
    }
	if (_ffmap) {
		getFFMap(bitcode);
	}
	if (_get_threads) {
		getThreads();
	}
	if (_instrument) {
		instrument(bitcode);
	}


    return 0;
}
 