FROM ubuntu:24.04

WORKDIR /hpc

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    ccache \
    cmake \
    g++ \
    git \
    wget \
    unzip \
    libfftw3-mpi-dev \
    libfftw3-dev \
    libhdf5-openmpi-dev \
    libopenmpi-dev \
    pkg-config \
    python3 \
    python3-dev \
    python3-matplotlib \
    python3-mpi4py \
    python3-numpy \
    python3-pandas \
    python3-pip \
    python3-scipy \
    python3-venv && \
    rm -rf /var/lib/apt/lists/*

RUN wget  https://github.com/BLAST-WarpX/warpx/archive/refs/tags/26.10.zip && \
    unzip 26.10.zip && \
    mv "warpx-26.10" warpx-src && \
    rm 26.10.zip 

RUN python3 -m venv --system-site-packages warpx-venv

ENV PATH="/hpc/warpx-venv/bin:/hpc/warpx/bin:${PATH}"

RUN python -m pip install -U \
    pip \
    build \
    packaging \
    "setuptools[core]" \
    wheel \
    cmake && \
    python -m pip install -r warpx-src/requirements.txt

RUN cmake -S warpx-src \
    -B warpx-build \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/hpc/warpx \
    -DPython_EXECUTABLE=/hpc/warpx-venv/bin/python \
    -DWarpX_MPI=ON \
    -DWarpX_COMPUTE=OMP \
    -DWarpX_DIMS=3 \
    -DWarpX_PYTHON=ON && \
    cmake --build warpx-build \
    --parallel 2 && \
    cmake --install warpx-build && \
    cmake --build warpx-build \
    --target pip_install \
    --parallel 2
    
RUN useradd -m -U -s /bin/bash warpx && \
    chown -R warpx:warpx /hpc

USER warpx

CMD ["/bin/bash"]