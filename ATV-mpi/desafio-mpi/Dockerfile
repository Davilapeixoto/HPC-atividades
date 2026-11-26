FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    openmpi-bin \
    libopenmpi-dev \
    python3 \
    python3-matplotlib \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m hpc

WORKDIR /app

RUN chown hpc:hpc /app

COPY --chown=hpc:hpc . .

RUN make entradas && \
    make gerar_texto mpi-letters mpi-letters-coletivas mpi-letters-p2p mpi-letters-allreduce

USER hpc

CMD ["/bin/bash"]
