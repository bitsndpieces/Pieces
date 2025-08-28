#include "svf-pieces.h"

extern FlowSensitive *fspta;
extern llvm::Module *ll_mod;
/*
Type* getInnermostPointedToType(Type* type) {
    while (type->isArrayTy() || type->isPointerTy()) {
        if (type->isArrayTy()) {
            type = cast<ArrayType>(type)->getElementType();
        } else if (type->isPointerTy()) {
            if (auto *ptrTy = dyn_cast<PointerType>(type)) {
                if (!ptrTy->isOpaque()) {
                    type = ptrTy->getNonOpaquePointerElementType();
                } else {
                    //errs() << "Opaque pointer\n";
                    return NULL;
                }
            }
        }
    }
    return type;
}

Type* getInnermostPointedToTypeOpaque(Value *val) {
    if (!val->getType()->isPointerTy()) return 
    for (auto *user : val.users()) {
        if (auto *inst = dyn_cast<Instruction>(val)) {
            switch (isnt->getOpcode()) {
                case Instruction::Load:
                case Instruction::Store:
                case Instruction::GetElementPtr:
                    if (inst->getType()->isPointerTy() || inst->getType()->isArrayTy()) {
                        auto *inner = getInnermostPointedToTypeOpaque(inst);
                        if (inner) return inner; 
                    } else {
                        return inst->getType();
                    }
            }
        }
    }
    return NULL;
}
*/
Value * getTaskFromTaskStruct(Value * elem) {
    //Get Task from task struct
    if (auto str2 = dyn_cast<llvm::ConstantStruct>(elem)) {
        cerr << "Constant Struct\n";
        auto functor = str2->getOperand(0);
        return functor;

        // 

        //if (auto str3 = dyn_cast<llvm::ConstantStruct>(functor)) {
        //    auto task = str3->getOperand(1);
        //    return task;
        //}
    }
    return NULL;
}

void getThreads() {
    ofstream threads;
    vector<llvm::Value *> thread_vec;
    threads.open("./out/threads");
    for (Function &F : *ll_mod) {
            Value * val = (Value *)&F;
            if (val->getName().str().compare("xTaskCreate")==0 || val->getName().str().compare("SafeTaskCreate")==0) {
                    cerr<<"xTaskCreate\n";
                    for (auto user : val->users()) {
                            if (auto ci =  dyn_cast<llvm::CallInst>(user)) {
                                    auto  thread = ci->getArgOperand(0);
                                    cerr<<thread<<endl;
                                    ci->print(errs());
                                    cerr<<thread->getName().str()<<endl;
                                    threads<<thread->getName().str()<<endl;
                                    thread_vec.push_back(thread);
                            }
                    }
            }
    }

    for (GlobalVariable &glob : ll_mod->globals()) {
        //auto ty = glob.getType();
        auto ty = glob.getValueType();
        //auto ity = getInnermostPointedToType(ty);
        //if (!ity) continue;
        auto ity = ty;
        if (auto str = dyn_cast<llvm::StructType>(ity)) 
        {
                cerr<<str->getNumElements()<<endl;
                if (str->getNumElements() == 8) {
                        cerr<<"Struct Type"<<endl;
                        cerr << glob.getName().str() << endl;
                        if (!str->isLiteral()) {
                                cerr<<"Literal Type" <<endl;
                                //Match signature of Task types
                                cerr << "check 1\n";
                                //ptr @prvRWAccessTask, ptr @.str.1.292, i16 256, ptr null, i32 1, ptr
                                if (str->getElementType(0)->isPointerTy() &&
                                                str->getElementType(1)->isPointerTy() &&
                                                str->getElementType(2)->isIntegerTy() &&
                                                str->getElementType(3)->isPointerTy() &&
                                                str->getElementType(4)->isIntegerTy(32)) {
                                        cerr<<"Structure Found\n";
                                        if (glob.hasInitializer()) {
                                                auto init = glob.getInitializer();
                                                cerr << init->getType()->getTypeID() << endl;
                                                //cerr << init->getType()->isStructTy() << endl;
                                                //cerr << init->getType()->isVectorTy() << endl;
                                                if (init->getType()->isArrayTy()) {
                                                    while(1) {};
                                                        unsigned NumElements = init->getNumOperands();
                                                        for (unsigned i = 0; i < NumElements; ++i) {
                                                                auto elem = init->getOperand(i);
                                                                //Get Task from task struct
                                                                auto task = getTaskFromTaskStruct(elem);
                                                                cerr<<"Adding a new array task"<<endl;
                                                                //task->dump();
                                                                threads<<task->getName().str()<<endl;
                                                                thread_vec.push_back(task);
                                                        }
                                                } else if (ty->isPointerTy() && false) {
                                                    while (1) {};
                                                        //TODO: Test this path

                                                } else if (init->getType()->isStructTy()) {
                                                        auto task = getTaskFromTaskStruct(init);
                                                        cerr << task->getName().str() << endl;
                                                } else {
                                                        //TODO: Test this path
                                                        auto task = getTaskFromTaskStruct(&glob);
                                                        cerr<<"Adding a new task"<<endl;
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