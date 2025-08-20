#include "svf-pieces.h"

extern FlowSensitive *fspta;
extern llvm::Module *ll_mod;

Type* getInnermostPointedToType(Type* type) {
    while (type->isArrayTy() || type->isPointerTy()) {
        if (type->isArrayTy()) {
            type = cast<ArrayType>(type)->getElementType();
        } else if (type->isPointerTy()) {
            if (auto *ptrTy = dyn_cast<PointerType>(type)) {
                if (!ptrTy->isOpaque()) {
                    type = ptrTy->getNonOpaquePointerElementType();
                } else {
                    errs() << "Opaque pointer, might be a problem\n";
                }
            }
        }
    }
    return type;
}

Value * getTaskFromTaskStruct(Value * elem) {
    //Get Task from task struct
    if (auto str2 = dyn_cast<llvm::ConstantStruct>(elem)) {
        auto functor = str2->getOperand(0);
        if (auto str3 = dyn_cast<llvm::ConstantStruct>(functor)) {
            auto task = str3->getOperand(1);
            return task;
        }
    }
    return NULL;
}

void getThreads() {

#ifdef FREERTOS
    ofstream threads;
    vector<llvm::Value *> thread_vec;
    threads.open("./out/threads");
    for (Function &F : *ll_mod) {
            Value * val = (Value *)&F;
            if (val->getName().str().compare("xTaskCreate")==0 || val->getName().str().compare("SafeTaskCreate")==0) {
                    for (auto user : val->users()) {
                            if (auto ci =  dyn_cast<llvm::CallInst>(user)) {
                                    auto  thread = ci->getArgOperand(0);
                                    threads<<thread->getName().str()<<endl;
                                    thread_vec.push_back(thread);
                            }
                    }
            }
    }
#endif

    for (GlobalVariable &glob : ll_mod->globals()) {
        auto ty = glob.getType();
        auto ity = getInnermostPointedToType(ty);
        if (auto str = dyn_cast<llvm::StructType>(ity)) 
        {
                if (str->getNumElements() == 5) {
                        cerr<<"Struct Type"<<endl;
                        if (str->isLiteral()) {
                                cerr<<"Literal Type" <<endl;
                                if (auto str1 = dyn_cast<llvm::StructType>(str->getElementType((unsigned int ) 0))) {
                                        //Match signature of Task types
                                        if (!str1->isLiteral() && str1->getStructName().contains("Functor")) {
                                                if (str->getElementType(1)->isPointerTy() &&
                                                                str->getElementType(2)->isFloatTy() &&
                                                                str->getElementType(3)->isIntegerTy(16) &&
                                                                str->getElementType(4)->isIntegerTy(8)) {
                                                        if (glob.hasInitializer()) {
                                                                auto init = glob.getInitializer();
                                                                if (init->getType()->isArrayTy()) {
                                                                        unsigned NumElements = init->getNumOperands();
                                                                        for (unsigned i = 0; i < NumElements; ++i) {
                                                                                auto elem = init->getOperand(i);
                                                                                //Get Task from task struct
                                                                                auto task = getTaskFromTaskStruct(elem);
                                                                                cerr<<"Adding a new task"<<endl;
                                                                                //task->dump();
                                                                                threads<<task->getName().str()<<endl;
                                                                                thread_vec.push_back(task);

                                                                        }
                                                                } else if (ty->isPointerTy()) {
                                                                        //TODO: Test this path

                                                                } else {
                                                                        //TODO: Test this path
                                                                        auto task = getTaskFromTaskStruct(&glob);
                                                                        //task->dump();
                                                                        threads<<task->getName().str()<<endl;
                                                                        thread_vec.push_back(task);
                                                                }
                                                        }
                                                }
                                        }
                                }
                        }
                }
        } 
    }

    if (fspta) {
		for (Function &F : *ll_mod) {
            Value * val = (Value *)&F;
            //F.getType()->dump();
            if (val->getName().str().compare("main")==0 ) {
                thread_vec.push_back(val);
                threads<<F.getName().str()<<endl;
            }
		}
	}
}