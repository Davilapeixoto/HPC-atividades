FROM ubuntu:24.04

WORKDIR /lettes

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    coreutils \
    time \
    procps \
    util-linux \
    python3 \
    python3-matplotlib \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -U -s /bin/bash omp && \
    chown -R omp:omp /lettes

USER omp

COPY --chown=omp:omp . /lettes

CMD ["/bin/bash"]