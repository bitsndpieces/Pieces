FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ARG TARGETPLATFORM

RUN set -e

ENV llvm_version=16

ENV HOME=/home/SVF-tools

ENV lib_deps="cmake g++ gcc git zlib1g-dev libncurses5-dev libtinfo6 build-essential libssl-dev libpcre2-dev zip libzstd-dev"
ENV build_deps="wget xz-utils git tcl software-properties-common"

# Update and install dependencies + LLVM/Clang 16
RUN apt-get update --fix-missing && \
    apt-get install -y $build_deps $lib_deps && \
    apt-get install -y clang-$llvm_version libclang-$llvm_version-dev llvm-$llvm_version-dev llvm-$llvm_version-tools llvm-$llvm_version && \
    rm -rf /var/lib/apt/lists/*

# Add deadsnakes PPA for Python 3.10 and install it
RUN add-apt-repository ppa:deadsnakes/ppa && apt-get update && \
    apt-get install -y python3.10-dev && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 && \
    rm -rf /var/lib/apt/lists/*

# Install libclang
RUN apt-get update && apt-get install -y python3-pip
RUN apt-get update && apt-get install -y python3-clang-16
RUN pip3 install -r /pieces/requirements.txt
RUN pip3 install ropgadget pyelftools networkx pydot

# Setup home and clone/build SVF
WORKDIR ${HOME}
RUN git clone https://github.com/SVF-tools/SVF.git
WORKDIR ${HOME}/SVF

RUN echo "Building SVF ..."
RUN bash ./build.sh

# Update PATHs to include LLVM/Clang binaries and SVF binaries
ENV PATH=${HOME}/SVF/Release-build/bin:/usr/lib/llvm-${llvm_version}/bin:$PATH
ENV SVF_DIR=${HOME}/SVF
ENV LLVM_DIR=/usr/lib/llvm-${llvm_version}

# (Optional) If you use Z3, make sure to build it or install it similarly,
# or adjust/remove the below link command accordingly
ENV Z3_DIR=${HOME}/SVF/z3.obj
RUN ln -s ${Z3_DIR}/bin/libz3.so ${Z3_DIR}/bin/libz3.so.4 || true



