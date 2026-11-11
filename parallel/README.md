## Exemplo de codigo de Subset Sum Problem
```c
#include <stdio.h>
#include <stdlib.h>
#include<time.h>

void displaySubset(int subSet[], int size)
{
   printf("One possible subset is:\n");
   for(int i = 0; i < size; i++)
   {
      printf("%d ",subSet[i]);
   }
   printf("\n");
}

void subsetSum(int set[], int subSet[], int n, int subSize, int total, int nodeCount ,int sum)
{
   if( total == sum)
   {
      displaySubset(subSet, subSize);     //print the subset
      return;     //for other subsets
   }
   else if(total < sum)
   {
      for( int i = nodeCount; i < n; i++ )
	  {     //find node along breadth
         subSet[subSize] = set[i];
         subsetSum(set,subSet,n,subSize+1,total+set[i],i+1,sum);     //do for next node in depth
      }
   }
}

void findSubset(int set[], int size, int sum)
{
   int *subSet = (int *)malloc(sizeof(int)*size);     //create subset array to pass parameter of subsetSum
   if (subSet == NULL)
      return;
   subsetSum(set, subSet, size, 0, 0, 0, sum);
   free(subSet);
}

int main()
{
    clock_t t;
    t = clock();
    int size=10;

   int weights[size];
   for(int i=0;i<size;i++)
    {
       weights[i]=i+1;
    }

   findSubset(weights, size, 10);
   t = clock() - t;
    double time_taken = ((double)t)/CLOCKS_PER_SEC; // in seconds

    printf("\nThis probelm took %f seconds to execute \n\n", time_taken);
 }
 ```

### 1. Decomposição
**Como você dividiria o trabalho entre os quatro trabalhadores? Represente sua ideia com um pequeno esquema ou pseudocódigo.**

Transformaria a busca em uma 'Arvore' e dividiria os quatros trabalhadores em ramos/galhos, onde eles podem incluir ou não um numero.

O trabalho seria dividido da seguinte forma:
- **T1:** inclui o primeiro e o segundo numero.
- **T2:** inclui o primeiro, mas não o segundo.
- **T3:** não inclui o primeiro, mas inclui o segundo.
- **T4:** não inclui nenhum dos dois primeiros numeros.

Apos a divisão, cada trabalhador continua explorando recursivamente e verificando quais combinações atingem a soma alvo.

**PseudoCodigo:**
```
INICIO
    Receber conjunto de numeros e soma-alvo

    PARALELO:
        T1: buscar(inclui N1, inclui N2)
        T2: buscar(inclui N1, exclui N2)
        T3: buscar(exclui N1, inclui N2)
        T4: buscar(exclui N1, exclui N2)

    Cada trabalhador:
        Explora os numeros restantes
        Armazena seus resultados localmente

    Aguarda todos os trabalhadores
    Combinar os resultados
FIM
```

### 2. Dependências e sincronização
**Os trabalhadores podem executar suas tarefas independentemente?**

Sim, os trabalhadres podem executar buscas independentemente, pois cada um explora uma parte diferente sem depender dos demais.

**Poderia ocorrer algum conflito ao atualizar o resultado?**

Sim, é possivel ocorrer condições de corridas caso os trabalhadores utilizem o mesmo vetor SubSet ou tentem modificar simultaneamente a estrutura de resultados.

### 3. Desempenho
**Quatro trabalhadores tornariam o programa quatro vezes mais rápido? Por quê?**

Não seria esperado obter um speedup de 4× ao utilizar quatro trabalhadores.

Segundo a Lei de Amdahl, a parte sequencial do programa limita o ganho de desempenho. Além disso, a distribuição dos ramos da árvore pode causar um desbalanceamento de carga, fazendo com que alguns trabalhadores terminem antes dos outros.

Os custos de criação, coordenação e sincronização dos trabalhadores também podem reduzir o speedup obtido.
