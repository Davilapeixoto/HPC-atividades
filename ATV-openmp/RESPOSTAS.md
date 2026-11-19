# Respostas às questões

### 01. Na sua máquina, a ingênua é mais rápida ou mais lenta que a serial? Por quê?

A Ingenua foi mais lenta que a Serial. Com 8 threads, levou 1,384 segundos, contra 0,722 segundos da Serial. Isso ocorreu pela disputa no acesso à memória compartilhada, causando perda de desempenho.

### 02. Critical e atomic corrigem. E o tempo, comparado com a serial? Por quê?

As duas corrigiram o resultado, mas ficaram mais lentas que a Serial. Com 16 threads, a Critical levou 49,396 segundos e a Atomic 3,113 segundos, contra 0,722 segundos da Serial. Isso acontece pelo custo de sincronização, já que a Critical permite apenas uma thread na região critica por vez, enquanto a Atomic sincroniza cada atualização individualmente.

### 03. O que acontece com schedule(dynamic, 1)? E com blocos maiores?

Com 8 threads, o `dynamic,1` levou 4,557 segundos, enquanto o `static` levou 0,165 segundos. Com blocos maiores (`dynamic,1024`), o tempo caiu para 0,112 segundos. Isso acontece porque distribuir uma iteração por vez aumenta muito o custo de gerenciamento das threads.

### 04. Até quantas threads o speedup cresce? Levante hipóteses e teste uma.

O speedup da Reduction continuou crescendo até 16 threads, chegando a 8,93 vezes. Uma hipótese era que o ganho diminuiria após os 8 núcleos físicos do processador. Nos testes, o speedup passou de 6,32 com 8 threads para 8,93 com 16, mostrando que o desempenho continuou melhorando, mas sem dobrar.

### 05. Sua versão: mais rápida ou mais lenta que a reduction? Por quê?

No nativo, a Reduction foi um pouco mais rápida, levando 0,080866 segundos contra 0,083475 segundos da Manual. No Docker, a Manual foi mais rápida, com 0,078966 segundos contra 0,082196 segundos da Reduction. As duas reduzem a disputa pelo histograma compartilhado, mas a Manual divide o texto diretamente entre as threads, enquanto a Reduction utiliza os mecanismos do OpenMP para combinar os resultados.

### 06. Opcional: sua máquina tem núcleos de tipos diferentes? Aparece nas medições?

O Ryzen 7 7735HS possui 8 núcleos físicos do mesmo tipo e 16 threads lógicas, utilizando SMT. Ele não possui núcleos de tipos diferentes.