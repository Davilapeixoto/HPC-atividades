# Desafio do histograma em MPI (Formação HPC, CESAR).
#
#   make                  compila letters (serial) e gerar_texto
#   make mpi-letters-xyz  compila mpi-letters-xyz.c (suas versões, com mpicc)
#   make entradas         gera os 3 textos de entrada e confere o SHA-256
#   make clean            apaga os executáveis (código e entradas ficam)

CC      = gcc
MPICC   = mpicc
CFLAGS  ?= -std=c99 -Wall -Wextra -Wpedantic -O2
# sha256sum (Linux) ou shasum -a 256 (macOS)
SHA256  := $(shell command -v sha256sum 2>/dev/null || echo "shasum -a 256")

.PHONY: all entradas clean

all: letters gerar_texto

mpi-letters%: mpi-letters%.c
	$(MPICC) $(CFLAGS) $< -o $@

letters: letters.c
	$(CC) $(CFLAGS) $< -o $@

gerar_texto: gerar_texto.c
	$(CC) $(CFLAGS) $< -o $@

# pequena: depurar (instantâneo) · media: conferir · grande: medir
entradas: gerar_texto
	mkdir -p entradas
	./gerar_texto 1M   > entradas/pequena.txt
	./gerar_texto 64M  > entradas/media.txt
	./gerar_texto 256M > entradas/grande.txt
	$(SHA256) -c entradas.sha256

# apaga só executáveis: os mpi-letters-*.c (suas versões) ficam
clean:
	rm -f letters gerar_texto $(patsubst %.c,%,$(wildcard mpi-letters-*.c))
