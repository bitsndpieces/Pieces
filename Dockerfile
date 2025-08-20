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

# Add deadsnakes PPA for Python 3.8 and install it
RUN add-apt-repository ppa:deadsnakes/ppa && apt-get update && \
    apt-get install -y python3.10-dev && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 && \
    rm -rf /var/lib/apt/lists/*
    


# Install libclang
RUN apt-get update && apt-get install -y python3-pip
RUN apt-get update && apt-get install -y python3-clang-16

COPY requirements.txt .
RUN pip3 install -r requirements.txt
RUN rm requirements.txt

RUN pip3 install ropgadget pyelftools networkx pydot

# Setup home and clone/build SVF
WORKDIR ${HOME}
RUN git clone https://github.com/SVF-tools/SVF.git
WORKDIR ${HOME}/SVF

RUN mkdir svf-llvm/tools/svf-pieces
COPY SVF/ svf-llvm/tools/svf-pieces/

RUN sed -i '1i add_subdirectory(svf-pieces)' svf-llvm/tools/CMakeLists.txt
RUN printf '/set(ALL_TOOLS/,/)/ {\n/)/a\\\nlist(APPEND ALL_TOOLS svf-pieces)\n}\n' > script.sed && \
    sed -i -f script.sed svf-llvm/tools/CMakeLists.txt && \
    rm script.sed

RUN echo "Building SVF ..."
RUN bash ./build.sh

# Update PATHs to include LLVM/Clang binaries and SVF binaries
#added autogen directory
ENV PATH=${HOME}/SVF/Release-build/bin:/usr/lib/llvm-${llvm_version}/bin:/pieces/partitioner/scripts:$PATH
ENV SVF_DIR=${HOME}/SVF
ENV LLVM_DIR=/usr/lib/llvm-${llvm_version}

# (Optional) If you use Z3, make sure to build it or install it similarly,
# or adjust/remove the below link command accordingly
ENV Z3_DIR=${HOME}/SVF/z3.obj
RUN ln -s ${Z3_DIR}/bin/libz3.so ${Z3_DIR}/bin/libz3.so.4 || true



