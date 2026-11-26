/****************************************************************************
 *
 * letters.c - Character counts
 *
 * Copyright (C) 2018--2026 Moreno Marzolla
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 ****************************************************************************/

/*
 * Versão serial para o desafio de MPI da Formação HPC (CESAR, 2026/2027), adaptada de
 * https://github.com/mmarzolla/parallel-etudes (omp-letters.c).
 * Modificado por Gabriel Freytag (CESAR) em 11/11/2026 e em 17/11/2026. Mudanças em
 * relação ao original:
 *   - só a versão serial (o enunciado e as soluções do original foram retirados);
 *   - lê a entrada padrão inteira, sem o limite de 5 MB;
 *   - make_hist() recebe o tamanho do texto (n), em vez de usar strlen(): um pedaço
 *     recebido por MPI_Scatter não termina em '\0';
 *   - índice do laço em size_t;
 *   - o caractere é lido como unsigned char, como pedem isalpha() e tolower();
 *   - main() confere se o total devolvido por make_hist() é a soma do histograma;
 *   - entrada vazia não gera divisão por zero em print_hist();
 *   - o tempo de make_hist() é medido com clock_gettime() (sem OpenMP) e sai na
 *     saída de erro, com 6 casas.
 * O texto completo da licença está no arquivo COPYING.
 *
 * Sua tarefa: escrever versões MPI deste programa (veja o README). O histograma
 * (hist) e o total de letras precisam sair iguais aos da versão serial.
 */

#define _POSIX_C_SOURCE 199309L   /* clock_gettime() com -std=c99 */
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <string.h>
#include <assert.h>
#include <time.h>

#define ALPHA_LEN 26

/**
 * Count occurrences of letters 'a'..'z' in the first `n` characters
 * of `text`; uppercase characters are transformed into lowercase, and
 * all other symbols are ignored. `text` does not need to be
 * zero-terminated. `hist` will be filled with the computed counts.
 * Returns the total number of letters found.
 */
int make_hist( const char *text, size_t n, int hist[ALPHA_LEN] )
{
    int nlet = 0; /* total number of alphabetic characters processed */

    /* Reset the histogram */
    for (int j=0; j<ALPHA_LEN; j++) {
        hist[j] = 0;
    }

    /* Count occurrences */
    for (size_t i=0; i<n; i++) {
        const unsigned char c = text[i];
        if (isalpha(c)) {
            const int idx = tolower(c) - 'a';
            nlet++;
            hist[idx]++;
        }
    }

    return nlet;
}

/**
 * If `freq == 100`, draw `len` caracters; otherwise, draw a fraction
 * of `len` characters proportional to `freq`.
 */
void bar( float freq, int len )
{
    for (int i=0; i<len*freq/100; i++) {
        printf("#");
    }
}

/**
 * Print frequencies
 */
void print_hist( int hist[ALPHA_LEN] )
{
    int nlet = 0;
    for (int i=0; i<ALPHA_LEN; i++) {
        nlet += hist[i];
    }
    for (int i=0; i<ALPHA_LEN; i++) {
        const float freq = (nlet > 0 ? 100.0*hist[i]/nlet : 0.0);
        printf("%c : %8d (%6.2f%%) ", 'a'+i, hist[i], freq);
        bar(freq, 65);
        printf("\n");
    }
    printf("    %8d total\n", nlet);
}

/**
 * Read all of standard input into a zero-terminated buffer.
 */
char *read_all( size_t *len )
{
    size_t cap = 1024*1024, n = 0, r;
    char *buf = (char*)malloc(cap); assert(buf != NULL);
    while ((r = fread(buf + n, 1, cap - n - 1, stdin)) > 0) {
        n += r;
        if (cap - n - 1 == 0) {
            cap *= 2;
            buf = (char*)realloc(buf, cap); assert(buf != NULL);
        }
    }
    buf[n] = '\0'; /* put a termination mark at the end of the text */
    *len = n;
    return buf;
}

/* relógio de parede, em segundos */
static double agora( void )
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

int main( void )
{
    int hist[ALPHA_LEN];
    size_t len;
    char *text = read_all(&len);
    const double tstart = agora();
    const int nlet = make_hist(text, len, hist);
    const double elapsed = agora() - tstart;
    print_hist(hist);
    fprintf(stderr, "Execution time %.6f s\n", elapsed);
    /* Confere o total devolvido por make_hist() contra a soma do histograma */
    int soma = 0;
    for (int j=0; j<ALPHA_LEN; j++) {
        soma += hist[j];
    }
    free(text);
    if (nlet != soma) {
        fprintf(stderr, "ERRO: make_hist() devolveu %d letras, mas o histograma soma %d\n", nlet, soma);
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
