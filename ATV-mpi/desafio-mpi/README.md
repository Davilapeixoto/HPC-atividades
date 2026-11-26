# Desafio: histograma de letras em MPI

Formação HPC · CESAR · aula de MPI (19/11/2026)

Este é o mesmo problema do desafio de OpenMP, agora com **processos que trocam mensagens**. Você recebe um programa **serial** que conta as letras de um texto: `letters.c`, adaptado de Moreno Marzolla (Univ. de Bologna, GPLv3). O desafio:

1. escrever versões MPI do programa;
2. conferir o resultado contra a versão serial;
3. **medir**, separando comunicação e computação, e comparar com o OpenMP.

Tudo dentro de um contêiner que você mesmo descreve. As entradas são **as mesmas** do desafio de OpenMP.

## Conteúdo

| Arquivo | O que é |
|---|---|
| `letters.c` | Versão serial. Lê o texto da entrada padrão e imprime o histograma. O tempo de `make_hist()` sai na saída de erro. |
| `gerar_texto.c` | Gera o texto de entrada. O mesmo tamanho e a mesma semente dão o mesmo arquivo, byte a byte, em qualquer máquina. |
| `Makefile` | Compila a serial (`gcc`), as suas versões (`mpicc`) e gera as entradas. |
| `entradas.sha256` | Hash esperado de cada entrada. |
| `COPYING` | Texto da licença GPLv3, que vale para `letters.c` e as versões derivadas dele. |

**O que mudou na serial em relação ao desafio de OpenMP:**
- `make_hist(text, n, hist)` agora recebe o tamanho `n` do texto, porque um pedaço recebido por `MPI_Scatter` não termina em `'\0'` (e `strlen` leria além do fim).
- O tempo é medido com `clock_gettime`, sem OpenMP.

## Primeiros passos

```bash
make             # compila letters (serial) e gerar_texto
make entradas    # gera entradas/pequena.txt, media.txt e grande.txt e confere o SHA-256
./letters < entradas/pequena.txt
```

| Arquivo | Tamanho | Para quê |
|---|---|---|
| `entradas/pequena.txt` | 1 MiB | Depurar: roda em milissegundos |
| `entradas/media.txt` | 64 MiB | Conferir as versões; é a entrada usada na aula |
| `entradas/grande.txt` | 256 MiB | Medir |

`make entradas` termina com três linhas `OK`. Se você ainda tem as entradas do desafio de OpenMP, elas são as mesmas: pode copiá-las.

Para compilar uma versão sua, crie `mpi-letters-<nome>.c` (copie `letters.c` e escreva o `main()` em MPI) e rode `make mpi-letters-<nome>`.

## O que fazer

1. **Três versões MPI**, cada uma num arquivo:
   - `mpi-letters-coletivas.c`: `MPI_Bcast` + `MPI_Scatterv` + `MPI_Reduce`, como na aula. Use `Scatterv` para que o texto seja dividido por completo mesmo quando o tamanho não é múltiplo do número de processos.
   - `mpi-letters-p2p.c`: a mesma lógica, mas os dados são distribuídos e combinados **só com `MPI_Send` e `MPI_Recv`**. O rank 0 manda a cada processo o seu pedaço e recebe de volta os histogramas. Dica: use tags diferentes para "pedaço" e "histograma". A medição de tempo pode usar `MPI_Barrier` e `MPI_Reduce`, como na outra versão.
   - **Uma versão sua**, que não está nos slides. Por exemplo:
     - cada processo lê o seu pedaço direto do arquivo, com `fopen` e `fseek`, sem `Scatter`. O nome do arquivo vai por argumento (`argv`), porque a entrada padrão chega só ao rank 0;
     - o rank 0 distribui os pedaços com `MPI_Isend`;
     - `MPI_Gather` dos histogramas e soma no rank 0;
     - `MPI_Allreduce`, para todos terem o histograma;
     - uma redução em árvore feita à mão com `Send`/`Recv`.

   Pode ser outra ideia. Na análise, diga por que escolheu essa versão e como ela se compara às outras.

   Contar letras não depende de onde o texto é cortado: não há problema de fronteira entre os pedaços.

2. **Conferir cada versão contra a serial**, com vários números de processos, **inclusive um que não divide o texto** (por exemplo, o número de núcleos da sua máquina). O histograma e o total precisam ser idênticos. Uma divisão que esquece o resto erra por poucas letras: só o `diff` pega. Teste também casos extremos: `-np 1`, um arquivo vazio e um texto com menos letras que processos (`printf "abc" > tres.txt`).

   ```bash
   ./letters < entradas/media.txt > serial.out
   for p in 1 2 3 4 8; do
       mpirun -np $p ./mpi-letters-coletivas < entradas/media.txt > paralelo.out \
           && diff -q serial.out paralelo.out && echo "$p processos: confere"
   done
   ```

3. **Medir** na entrada grande, com 1, 2, 4 e 8 processos e com o número de núcleos físicos da máquina, repetindo cada medição pelo menos 5 vezes e usando a mediana. Meça com `MPI_Wtime()`:
   - **distribuir** (do `MPI_Bcast` ao fim do `Scatterv`), **contar** e **combinar** (o `Reduce`);
   - em cada fase, vale o **processo mais lento** (`MPI_Reduce` com `MPI_MAX` dos tempos). Os máximos das fases são diagnóstico: podem vir de processos diferentes, e a soma deles pode passar de T(p);
   - a leitura do arquivo e a impressão ficam de fora;
   - **T(p)** é o maior tempo total entre os processos: `MPI_MAX` de `t3 - t0`, onde `t0` é logo depois da barreira e `t3` o fim do `Reduce`. T_serial é o tempo de `make_hist()` da serial.

4. **Speedup** S = T_serial / T(p) e **eficiência** E = S / p, numa tabela e num gráfico, mais as fases separadas. **Compare com a melhor versão OpenMP** do desafio anterior, na mesma máquina e na mesma entrada.

5. **Contêiner:** compile e meça dentro dele (próxima seção).

## Rodar com mpirun: cuidados

- **Quantos processos cabem:** por padrão, o Open MPI aceita um processo por **núcleo físico**, não por thread de hardware. Numa máquina com 10 núcleos e 12 threads, `mpirun -np 11` falha com "not enough slots". Para usar as threads de hardware: `mpirun --use-hwthread-cpus -np 12`. Para passar do limite: `mpirun --oversubscribe -np 16` (funciona, mas os processos disputam núcleos).
- **Entrada padrão:** `mpirun ... < arquivo` entrega a entrada **só ao rank 0**. Os argumentos da linha de comando chegam a todos.
- **Saída misturada:** os processos imprimem ao mesmo tempo; `--tag-output` mostra o rank de cada linha.
- **Afinidade:** o Open MPI prende cada processo a um núcleo quando há até 2 processos e a um socket quando há mais. `--report-bindings` mostra o que foi feito.
- **Root:** o `mpirun` se recusa a rodar como root. Rode como usuário comum ou veja a seção do Docker.
- **"Authorization required, but no authorization protocol specified"** repetido a cada execução, numa sessão gráfica: é o hwloc tentando a interface gráfica. Não atrapalha; para sumir, `export HWLOC_COMPONENTS=-gl`.

## Ambiente em contêiner

Continue a receita que você escreveu no desafio de OpenMP e acrescente o MPI. A receita precisa:

- partir de `ubuntu:24.04` (traz o GCC 13 e o Open MPI 4.1.6, a versão usada na aula);
- instalar `gcc`, `libc6-dev`, `make`, `openmpi-bin` e `libopenmpi-dev` (`libc6-dev` vem junto com o `gcc`, exceto com `--no-install-recommends`).

**Recomendado: Apptainer (antigo Singularity).** O `mpirun` roda **dentro** do contêiner, e a imagem enxerga a pasta atual e os núcleos da máquina. Escreva um `mpi.def`:

```bash
apptainer build mpi.sif mpi.def      # se pedir root: apptainer build --fakeroot mpi.sif mpi.def
apptainer exec mpi.sif make
apptainer exec mpi.sif make mpi-letters-coletivas    # depois de escrever mpi-letters-coletivas.c
apptainer exec mpi.sif mpirun -np 4 ./mpi-letters-coletivas < entradas/grande.txt
```

Com SingularityCE, troque `apptainer` por `singularity`.

**Alternativa: Docker.** O contêiner roda como root, e o `mpirun` recusa. Há duas saídas:
- rodar como o seu usuário, com `-u "$(id -u):$(id -g)"` (os arquivos criados também ficam seus); ou
- pôr no `Dockerfile` as variáveis `OMPI_ALLOW_RUN_AS_ROOT=1` e `OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1`.

```bash
docker build -t mpi .
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD":/work -w /work mpi make mpi-letters-coletivas
docker run --rm -i -u "$(id -u):$(id -g)" -v "$PWD":/work -w /work mpi \
    mpirun -np 4 ./mpi-letters-coletivas < entradas/grande.txt
```

Com o Podman sem root, troque `-u "$(id -u):$(id -g)"` por `--userns=keep-id`.

**Pergunta:** quantos processos o `mpirun` aceita dentro do contêiner? E fora dele?

## Para investigar

Responda com base nas **suas** medições.

- Onde está o tempo com 1 processo e com 8? A partir de quantos processos a comunicação passa a dominar?
- Na sua máquina, MPI ou OpenMP é mais rápido para este problema? Por quê?
- A versão p2p é mais lenta que a de coletivas? Por quê (ou por que não)?
- Rode com `--report-bindings`. O que muda entre 2 e 4 processos? E com `--bind-to core`?
- O que acontece com mais processos que núcleos físicos (`--use-hwthread-cpus` e `--oversubscribe`)?
- Se o texto estivesse espalhado em 4 máquinas, o que mudaria no seu código?
- Sua versão própria é mais rápida ou mais lenta que a de coletivas? Por quê?
- Opcional, como no Encontro 2: dispersão das repetições, throughput (MiB/s) e tempo de CPU contra tempo de parede.

## Entrega

- O código das três versões;
- a receita do contêiner (`mpi.def` ou `Dockerfile`);
- a tabela de speedup e eficiência com as fases separadas, o gráfico e a comparação com o OpenMP;
- a descrição do ambiente da medição: CPU, núcleos físicos e lógicos, compilador, versão do MPI, nativo ou contêiner;
- uma análise curta, respondendo às perguntas acima.

## Sobre a solução de Bologna

O repositório de Marzolla tem um `mpi-letters.c` com uma solução pública. Consulte se quiser, como **ideia, não para copiar**: com as nossas entradas ela não funciona sem ajustes. O `text_len` é `int` mas é transmitido como `MPI_LONG`; o cálculo do início e do fim de cada pedaço estoura `int` na entrada grande; ela usa `isalpha` com `char`; e lê no máximo 5 MB. Encontrar esses problemas é um bom exercício opcional.

## Observações

- **Windows:** use o WSL2 com o contêiner.
- **Memória:** o rank 0 lê a entrada inteira para a memória. Na entrada grande, reserva 512 MiB, e o pico pode passar disso durante a leitura; cada processo ainda recebe uma cópia do seu pedaço.
- **Letras:** o programa conta só as letras de `a` a `z`, sem acento (ASCII).
- **Créditos e licença:** `letters.c` © 2018–2026 Moreno Marzolla, GPLv3, adaptado de <https://github.com/mmarzolla/parallel-etudes> (as mudanças estão no comentário do início do arquivo). As suas versões, derivadas dele, também são GPLv3; o texto da licença está em `COPYING`.
