mkdir llvm_12
cd llvm_12

wget https://github.com/llvm/llvm-project/releases/download/llvmorg-12.0.0/llvm-12.0.0.src.tar.xz
tar -xvf llvm-12.0.0.src.tar.xz
mv llvm-12.0.0.src llvm

wget https://github.com/llvm/llvm-project/releases/download/llvmorg-12.0.0/clang-12.0.0.src.tar.xz
tar -xvf clang-12.0.0.src.tar.xz
mv clang-12.0.0.src clang

wget https://github.com/llvm/llvm-project/releases/download/llvmorg-12.0.0/compiler-rt-12.0.0.src.tar.xz
tar -xvf compiler-rt-12.0.0.src.tar.xz
mv compiler-rt-12.0.0.src compiler-rt

mkdir llvm-12.0.0.obj
cd llvm-12.0.0.obj

cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Debug \
  -DLLVM_BUILD_LLVM_DYLIB=ON -DLLVM_LINK_LLVM_DYLIB=ON \
  -DLLVM_ENABLE_RTTI=ON -DLLVM_TARGETS_TO_BUILD="X86;ARM;AArch64;Mips" -DLLVM_ENABLE_PROJECTS="clang;compiler-rt" \
  ../llvm

make llvm-headers
make -j12
