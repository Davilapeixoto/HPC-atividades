# Desafio: histograma de letras em OpenMP

Formação HPC · CESAR · aula de OpenMP (12/11/2026)

Você recebe um programa **serial** que conta as letras de um texto: `omp-letters.c`, adaptado de Moreno Marzolla (Univ. de Bologna, GPLv3). O desafio:

1. paralelizar o programa com OpenMP;
2. conferir o resultado contra a versão serial;
3. **medir**.

Tudo dentro de um contêiner que você mesmo descreve. Todos partem do mesmo código e da mesma entrada. A ideia não é virar especialista, e sim experimentar o que vimos em aula e entender o que acontece.

## Conteúdo

| Arquivo | O que é |
|---|---|
| `omp-letters.c` | Versão serial. Lê o texto da entrada padrão e imprime o histograma. O tempo de `make_hist()` sai na saída de erro. |
| `gerar_texto.c` | Gera o texto de entrada. O mesmo tamanho e a mesma semente dão o mesmo arquivo, byte a byte, em qualquer máquina. |
| `Makefile` | Compila os programas e gera as entradas. |
| `entradas.sha256` | Hash esperado de cada entrada. |
| `COPYING` | Texto da licença GPLv3, que vale para `omp-letters.c` e as versões derivadas dele. |

**Requisito:** GCC com OpenMP e `make`, em Linux ou WSL2. No macOS, o `clang` da Apple não traz OpenMP; use o contêiner ou veja as observações no fim.

## Primeiros passos

```bash
make             # compila omp-letters (serial) e gerar_texto
make entradas    # gera entradas/pequena.txt, media.txt e grande.txt e confere o SHA-256
./omp-letters < entradas/pequena.txt
```

As três entradas:

| Arquivo | Tamanho | Para quê |
|---|---|---|
| `entradas/pequena.txt` | 1 MiB | Depurar: roda em milissegundos |
| `entradas/media.txt` | 64 MiB | Conferir as versões; é a entrada usada na aula |
| `entradas/grande.txt` | 256 MiB | Medir: tempo suficiente para o speedup aparecer |

`make entradas` termina com três linhas `OK`. Se alguma der `FAILED`, sua entrada não é igual à dos colegas: rode `make clean`, depois `make entradas` de novo, e avise no Slack se continuar.

## O que fazer

1. **Quatro versões paralelas** de `make_hist()`, cada uma num arquivo. Três são as vistas em aula:
   - `omp-letters-critical.c` (ou `-atomic`): proteger as atualizações compartilhadas;
   - `omp-letters-local.c`: um histograma por thread, combinado no fim;
   - `omp-letters-reduction.c`: deixar o OpenMP fazer a combinação.

   A quarta é **sua**: uma versão que não está nos slides, à sua escolha. Por exemplo:
   - `omp-letters-tasks.c`: o texto dividido em blocos, um bloco por task;
   - `omp-letters-matriz.c`: os histogramas locais num array `[thread][26]` compartilhado, sem e com espaçamento entre as linhas;
   - `omp-letters-manual.c`: a divisão do texto feita na mão, com `omp_get_thread_num()` e `omp_get_num_threads()`, sem `omp for`.

   Pode ser outra ideia. Na análise, diga por que escolheu essa versão e como ela se compara às outras.

   Copie `omp-letters.c` e altere só `make_hist()`. Para compilar, use `make omp-letters-reduction` (vale para qualquer `omp-letters-<nome>.c`).

   Crie também `omp-letters-ingenua.c`, só com `#pragma omp parallel for` no laço, para observar a condição de corrida. Ela não conta como solução: serve para comparar.

2. **Conferir cada versão contra a serial**, com vários números de threads. O histograma precisa ser idêntico, e o total devolvido por `make_hist()` também precisa estar certo: o `main()` confere esse total e, se ele não bater com o histograma, imprime `ERRO` e termina com falha.

   ```bash
   ./omp-letters < entradas/media.txt > serial.out
   for p in 1 2 4 8; do
       OMP_NUM_THREADS=$p ./omp-letters-reduction < entradas/media.txt > paralelo.out \
           && diff -q serial.out paralelo.out && echo "$p threads: confere"
   done
   ```

   Uma versão com condição de corrida pode acertar de vez em quando: repita a conferência algumas vezes.

3. **Medir** com 1, 2, 4 e 8 threads e com o máximo da sua máquina (`nproc`), na entrada grande. Repita cada medição pelo menos 5 vezes e use a mediana. O tempo impresso é só o de `make_hist()`, sem a leitura do arquivo e sem a impressão. `OMP_NUM_THREADS` pede um número de threads. A linha do tempo mostra `omp_get_max_threads()`: o limite de threads para uma nova região paralela, não a contagem de threads que de fato rodaram:

   ```bash
   OMP_NUM_THREADS=4 ./omp-letters-reduction < entradas/grande.txt > /dev/null
   ```

4. **Speedup** S = T_serial / T(p) e **eficiência** E = S / p, numa tabela e num gráfico. T_serial é o tempo da versão serial (`omp-letters`), e T(p) o da sua versão com p threads. Compare também T_serial com T(1): a diferença é o custo do OpenMP com uma thread só.

5. **Contêiner:** compile e meça dentro dele (próxima seção).

## Ambiente em contêiner

Este é o ponto de encontro com a aula de contêineres: escreva a receita do seu ambiente e rode o desafio dentro dele. A receita precisa:

- partir de uma imagem Linux com GCC 12 ou mais novo (por exemplo, `ubuntu:24.04`);
- instalar o compilador, a biblioteca do OpenMP e o `make`.

**Recomendado: Apptainer (antigo Singularity).** A imagem é um único arquivo `.sif` e executa sem root. Ela já enxerga a pasta atual, todos os núcleos e as variáveis de ambiente, como `OMP_NUM_THREADS`. Funciona em Linux e no WSL2. Escreva um `hist.def`:

```bash
apptainer build hist.sif hist.def      # se pedir root: apptainer build --fakeroot hist.sif hist.def
apptainer exec hist.sif make
OMP_NUM_THREADS=8 apptainer exec hist.sif ./omp-letters < entradas/grande.txt
```

Com SingularityCE, troque `apptainer` por `singularity`.

**Alternativa: Docker.** Roda também no macOS e no Windows. Escreva um `Dockerfile` com os mesmos requisitos. O contêiner não enxerga sua pasta nem suas variáveis, então monte a pasta com `-v` e passe as variáveis com `-e`:

```bash
docker build -t hist .
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD":/work -w /work hist make
docker run --rm -i -e OMP_NUM_THREADS=8 -v "$PWD":/work -w /work hist \
    ./omp-letters < entradas/grande.txt
```

O `-u` faz os arquivos criados pertencerem a você, e não ao root. No macOS e no Windows, o Docker roda numa máquina virtual com um número limitado de CPUs (veja as configurações do Docker Desktop).

**Pergunta:** o tempo dentro do contêiner muda em relação ao nativo? Meça e explique.

## Para investigar

Responda com base nas **suas** medições: os resultados mudam de máquina para máquina.

- Na sua máquina, a versão ingênua (só `#pragma omp parallel for`), além de errada, é mais rápida ou mais lenta que a serial? Por quê?
- `critical` e `atomic` corrigem o resultado. E o tempo, como fica em relação à serial? Por quê?
- O que acontece com `schedule(dynamic, 1)`? E com blocos maiores?
- Até quantas threads o speedup cresce? Onde ele para de crescer, levante hipóteses (núcleos físicos e lógicos, tipos de núcleo, frequência, custo de coordenação, memória) e teste pelo menos uma.
- Sua versão própria é mais rápida ou mais lenta que a `reduction`? Por quê?
- Opcional: sua máquina tem núcleos de tipos diferentes (P-cores e E-cores)? Isso aparece nas medições?
- Opcional, como no Encontro 2: relate também a dispersão das repetições (mínimo e máximo, ou desvio padrão), o throughput (MiB/s = tamanho da entrada / tempo) e o tempo de CPU contra o tempo de parede (`user` e `real` do `time`) com 1 e com 8 threads. O que cada um mostra?

## Entrega

- O código das versões, incluindo a sua;
- a receita do contêiner (`hist.def` ou `Dockerfile`);
- a tabela de speedup e eficiência, com o gráfico;
- a descrição do ambiente da medição: CPU, núcleos físicos e lógicos, compilador e flags, nativo ou contêiner;
- uma análise curta, respondendo às perguntas acima.

As soluções de Bologna são públicas: consulte se quiser. O que conta é a **sua** medição e a **sua** análise.

## Observações

- **Windows:** use o WSL2 ou o contêiner. No PowerShell, o redirecionamento `>` pode mudar a codificação do texto gerado.
- **macOS sem contêiner:** instale o GCC (`brew install gcc`) e compile com `make CC=gcc-14` (use o número da versão instalada). O hash é conferido com `shasum -a 256`, e o Makefile já faz isso sozinho.
- **Memória:** o programa lê a entrada inteira para a memória. Na entrada grande, reserva 512 MiB, e o pico pode passar disso durante a leitura. Numa VM ou no Docker Desktop com pouca memória, comece pela entrada média.
- **Letras:** o programa conta só as letras de `a` a `z`, sem acento (ASCII). Num texto em UTF-8, letras acentuadas e outros símbolos são ignorados.
- **Créditos e licença:** `omp-letters.c` © 2018–2026 Moreno Marzolla, GPLv3, adaptado de <https://github.com/mmarzolla/parallel-etudes> (as mudanças estão no comentário do início do arquivo). As suas versões, derivadas dele, também são GPLv3; o texto da licença está em `COPYING`.
