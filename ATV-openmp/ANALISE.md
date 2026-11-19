# Analise dos Resultados

Os testes rodaram com a entrada de 256 MiB. Com 1,2,4,8 e 16 Threads, cada uma com 5 repetições.

A versão ingenua apresentou resultados incorretos quando foi utilizado MultiThreads, o resultado incorreto foi causado pela condição de corrida(Race Condition) no acesso ao histograma compartilhado. Esse problema foi corrigido nas outras implementações.

As versões Critical e Atomic foram as mais lentas. Mesmo paralelizadas, ficaram mais lentas que a Serial. A Critical teve o pior desempenho, sendo executada em 49,396 segundos com 16 threads. Isso se deve ao funcionamento do Critical, onde apenas uma thread pode acessar a região crítica por vez, enquanto as outras esperam. Já o Atomic tem um funcionamento parecido, mas protege operações individuais em vez de um bloco inteiro.

Já as versões Local, Manual e Reduction obtiveram os melhores resultados utilizando 16 Threads. No nativo, o Reduction foi mais rapido, com 0,080866 segundo, enquanto a Manual levou 0,083475 segundo.   Já no Docker, a Manual foi a mais rápida, com 0,078966 segundo, contra 0,082196 segundo do Reduction. Isso acontece porque essas versões reduzem a disputa pelo recurso compartilhado.

O speedup da Reduction chegou a 8,93 vezes com 16 threads. Nos testes de Schedule, o dynamic,1 foi o mais lento, levando 4,557 segundos com 8 threads, enquanto o static levou 0,165 segundo. Com blocos maiores (dynamic,1024), o tempo caiu para 0,112 segundo.

Um detalhe interessante é que na comparação entre ambientes, o Docker foi mais rapido em 98 de 150 execuções validas. Essa diferença pode estar relacionada às versões do GCC utilizadas, já que no Linux nativo foi usado o GCC 16.2.1, enquanto no Docker foi usado o GCC 13.3.0.