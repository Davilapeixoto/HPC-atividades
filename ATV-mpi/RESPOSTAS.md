# Respostas — Desafio MPI

**1. Onde está o tempo com 1 e 8 processos? Quando a comunicação passa a dominar?**

Com 1 e 8 processos, a maior parte do tempo está na contagem das letras. Com 16 processos, a comunicação passa a ter um peso maior nas versões Coletivas e Allreduce, enquanto na P2P a contagem ainda predomina. Como os maiores tempos de cada fase podem vir de processos diferentes, não podemos afirmar que a comunicação domina o tempo total.

**2. MPI ou OpenMP é mais rápido? Por quê?**

O OpenMP foi mais rápido. A versão Manual levou 78,966 ms, enquanto a melhor versão MPI, a P2P, levou 127,647 ms, ambas com 16 trabalhadores. Isso é causado pelo uso de memória compartilhada no OpenMP, que evita a necessidade de distribuir o texto entre os processos.

**3. A P2P é mais lenta que a Coletivas?**

Até 8 processos, sim. Com 16 processos, a P2P foi ligeiramente mais rápida, com 127,647 ms contra 128,180 ms da Coletivas.

**4. O que muda na afinidade entre 2 e 4 processos?**

Com 2 processos, cada rank ficou associado a um núcleo físico. Com 4 processos, os ranks ficaram livres para utilizar os núcleos disponíveis. Ao utilizar `--bind-to core`, cada rank ficou associado a um núcleo específico. O Docker apresentou um aviso relacionado à vinculação de memória, mas os programas executaram normalmente e os tempos foram semelhantes.

**5. O que acontece com mais processos que núcleos físicos?**

Tanto no Docker quanto no CachyOS, o limite padrão foi de 8 processos. Ao tentar executar com 9, o MPI apresentou um erro por falta de slots. Com `--use-hwthread-cpus`, foi possível executar com 16 processos. Utilizando também o `--oversubscribe`, foi possível executar com 17 processos, porém o tempo aumentou de 124,253 ms para 151,004 ms.

**6. Se o texto estivesse espalhado em quatro máquinas, o que mudaria?**

Cada máquina poderia ler e contar as letras do seu próprio trecho. Dessa forma, não seria necessário enviar todo o texto pelo rank 0, apenas combinar os histogramas de cada máquina pela rede.

**7. A versão própria é mais rápida ou mais lenta que a Coletivas? Por quê?**

Foi utilizado o `MPI_Allreduce`. Nos testes, essa versão foi um pouco mais lenta que a Coletivas em todas as configurações. Isso é causado pelo custo adicional de disponibilizar o resultado para todos os processos.