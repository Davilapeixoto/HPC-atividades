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
#include <mpi.h>

#define ALPHA_LEN 26

/**
 * Count occurrences of letters 'a'..'z' in the first `n` characters
 * of `text`; uppercase characters are transformed into lowercase, and
 * all other symbols are ignored. `text` does not need to be
 * zero-terminated. `hist` will be filled with the computed counts.
 * Returns the total number of letters found.
 */
int make_hist( const char *text, size_t n, int hist[ALPHA_LEN], double tempos[4] )
{
    int nlet = 0; /* total number of alphabetic characters processed */
    int size,rank,deslocamento = 0;

    MPI_Barrier(MPI_COMM_WORLD);
    double t0 = MPI_Wtime();

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

        
    char *char_local = NULL;
    int media=n/size, tamanho[size], passos[size];

    for(int j=0; j<size; j++){
        tamanho[j]=media + ((size_t)j < (n % size));
        passos[j]=deslocamento;
        deslocamento += tamanho[j];
    }

    /* Reset the histogram */
    for (int j=0; j<ALPHA_LEN; j++) {
        hist[j] = 0;
    }

    if(rank==0){
        for(int j=1; j<size; j++)MPI_Send(&n, 1, MPI_UNSIGNED_LONG, j, 0, MPI_COMM_WORLD);
        
        for(int j=1; j<size;j++) MPI_Send(text + passos[j], tamanho[j], MPI_CHAR, j, 1, MPI_COMM_WORLD);


        char_local= malloc((size_t)tamanho[0] + 1);
        assert(char_local != NULL);
        memcpy(char_local, text, tamanho[0]);
    } else{
        MPI_Recv(&n, 1, MPI_UNSIGNED_LONG, 0, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);

        tamanho[rank] = n/size + ((size_t)rank < (n % size));
        char_local = malloc((size_t)tamanho[rank] + 1);
        assert(char_local != NULL);

        MPI_Recv(char_local, tamanho[rank], MPI_CHAR, 0, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
    }
    
    double t1 = MPI_Wtime();

    /* Count occurrences */
    for (size_t i=0; i<(size_t)tamanho[rank]; i++) {
        const unsigned char c = char_local[i];
        if (isalpha(c)) {
            const int idx = tolower(c) - 'a';
            nlet++;
            hist[idx]++;
        }
    }

    double t2 = MPI_Wtime();

    if(rank==0){
        int aux_hist[ALPHA_LEN],aux_nlet;

        for(int i=1; i<size;i++){
            MPI_Recv(aux_hist, 26, MPI_INT, i, 2, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            MPI_Recv(&aux_nlet, 1, MPI_INT, i, 3, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            for(int j=0; j<26;j++){
                hist[j]+=aux_hist[j];
            }

            nlet+=aux_nlet;
        }
    } else{
        MPI_Send(hist, 26,MPI_INT, 0, 2, MPI_COMM_WORLD);
        MPI_Send(&nlet, 1,MPI_INT, 0, 3, MPI_COMM_WORLD);
    }

    double t3 = MPI_Wtime();

    double meu[4] = {t1-t0,t2-t1,t3-t2,t3-t0};
    MPI_Reduce(meu, tempos, 4, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    
    free(char_local);
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

int main( void )
{
    MPI_Init(NULL, NULL);

    int rank;

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    
    int hist[ALPHA_LEN];
    size_t len=0;
    double tempos[4];
    
    char *text = NULL;

    if(rank==0) text = read_all(&len);

    const int nlet = make_hist(text, len, hist, tempos);
    
    MPI_Finalize();

    if(rank == 0){
        print_hist(hist);
        fprintf(stderr, "Execution time %.6f s\n", tempos[3]);
        fprintf(stderr, "Phases %.6f %.6f %.6f s\n", tempos[0],tempos[1],tempos[2]);
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
}