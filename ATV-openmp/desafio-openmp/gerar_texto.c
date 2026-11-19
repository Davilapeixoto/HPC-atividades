/*
 * gerar_texto.c — gera um texto ASCII pseudoaleatório e determinístico para o
 * desafio do histograma de letras (Formação HPC CESAR 2026/2027).
 *
 * Mesmo (tamanho, semente) => mesmo arquivo, byte a byte, em qualquer máquina:
 * o gerador usa só aritmética inteira de 64 bits (SplitMix64) e uma tabela fixa
 * de frequências; não depende de rand(), locale nem ponto flutuante.
 *
 * Compilar:  gcc -O2 -std=c99 -Wall -o gerar_texto gerar_texto.c
 * Usar:      ./gerar_texto <tamanho> [semente] > entrada.txt
 *            tamanho aceita sufixos K, M, G (potências de 1024). Ex.: 256M, 1G
 * Conferir:  sha256sum entrada.txt
 *
 * Portável por construção: só inteiros de tamanho fixo e bytes ASCII ('\n' como fim de linha,
 * inclusive no Windows); não depende de endianness, libc, compilador nem otimização.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

/* SplitMix64 (Steele, Lea & Flood, 2014): simples, rápido e portável. */
static uint64_t estado;
static uint64_t proximo(void)
{
    uint64_t z = (estado += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

/* Inteiro uniforme em [0, n): rejeição evita viés do módulo. */
static uint32_t sorteia(uint32_t n)
{
    const uint64_t limite = UINT64_MAX - (UINT64_MAX % n);
    uint64_t x;
    do { x = proximo(); } while (x >= limite);
    return (uint32_t)(x % n);
}

/* Frequência aproximada das letras em inglês, em partes por 10000 (soma = 10000). */
static const uint16_t peso[26] = {
    817, 149, 278, 425, 1270, 223, 202, 609, 697, 15, 77, 403, 241,
    675, 751, 193, 10, 599, 633, 906, 276, 98, 236, 15, 197, 5
};
static uint16_t acumulado[26];

static char letra(void)
{
    const uint32_t r = sorteia(10000);
    int i = 0;
    while (r >= acumulado[i]) i++;
    return (char)('a' + i);
}

static unsigned long long le_tamanho(const char *s)
{
    char *fim;
    unsigned long long v = strtoull(s, &fim, 10);
    switch (*fim) {
    case 'K': case 'k': v <<= 10; break;
    case 'M': case 'm': v <<= 20; break;
    case 'G': case 'g': v <<= 30; break;
    case '\0': break;
    default: fprintf(stderr, "tamanho inválido: %s\n", s); exit(EXIT_FAILURE);
    }
    return v;
}

int main(int argc, char *argv[])
{
    if (argc < 2 || argc > 3) {
        fprintf(stderr, "uso: %s <tamanho[K|M|G]> [semente]\n", argv[0]);
        return EXIT_FAILURE;
    }
    const unsigned long long total = le_tamanho(argv[1]);
    estado = (argc == 3) ? strtoull(argv[2], NULL, 10) : 2026;

    uint16_t s = 0;
    for (int i = 0; i < 26; i++) { s += peso[i]; acumulado[i] = s; }

#ifdef _WIN32
    /* No Windows, stdout em modo texto trocaria '\n' por "\r\n" e mudaria o arquivo. */
    _setmode(_fileno(stdout), _O_BINARY);
#endif
    static char buf[1 << 16];
    size_t n = 0;
    unsigned long long escritos = 0;
    int coluna = 0, inicio_frase = 1;

    while (escritos < total) {
        /* Uma palavra de 1 a 12 letras. */
        const int len = 1 + (int)sorteia(12);
        for (int k = 0; k < len; k++) {
            char c = letra();
            if (k == 0 && (inicio_frase || sorteia(20) == 0)) c = (char)(c - 'a' + 'A');
            buf[n++] = c;
            coluna++;
        }
        inicio_frase = 0;

        /* Pontuação ocasional (caracteres que não são letras). */
        const uint32_t p = sorteia(100);
        if (p < 6)       { buf[n++] = '.'; coluna++; inicio_frase = 1; }
        else if (p < 12) { buf[n++] = ','; coluna++; }
        else if (p < 13) { buf[n++] = ';'; coluna++; }

        /* Quebra de linha perto da coluna 72; senão, espaço. */
        if (coluna >= 72) { buf[n++] = '\n'; coluna = 0; }
        else              { buf[n++] = ' ';  coluna++; }

        if (n > sizeof(buf) - 32) {
            size_t m = n;
            if (escritos + m > total) m = (size_t)(total - escritos);
            fwrite(buf, 1, m, stdout);
            escritos += m;
            n = 0;
        }
    }
    return EXIT_SUCCESS;
}
