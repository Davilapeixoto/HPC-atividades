#!/usr/bin/env python3
"""Gera os gráficos a partir de resultados/resumo.csv, sem repetir o benchmark."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

NOMES = {'serial':'Serial','coletivas':'Coletivas','p2p':'P2P','allreduce':'Allreduce','openmp':'OpenMP'}
VERSOES = ('coletivas','p2p','allreduce','openmp')
FASES = [('distribuir_mediana_s','Distribuir'),('contar_mediana_s','Contar'),('combinar_mediana_s','Combinar')]


def numero(row, chave):
    return float(row[chave]) if row.get(chave) not in ('',None) else None


def salvar(fig, destino):
    fig.tight_layout()
    fig.savefig(destino,dpi=180,bbox_inches='tight')
    plt.close(fig)
    print(destino)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--resultados',type=Path,default=Path('resultados'))
    args=ap.parse_args()
    fonte=args.resultados/'resumo.csv'
    if not fonte.is_file(): ap.error(f'Arquivo não encontrado: {fonte}. Execute o benchmark antes.')
    with fonte.open(encoding='utf-8',newline='') as f:
        dados=list(csv.DictReader(f))
    if not dados: ap.error('resumo.csv vazio')
    saida=args.resultados/'graficos'; saida.mkdir(parents=True,exist_ok=True)
    for entrada in dict.fromkeys(r['entrada'] for r in dados):
        rows=[r for r in dados if r['entrada']==entrada]
        serial=next(r for r in rows if r['versao']=='serial')
        series={v:sorted([r for r in rows if r['versao']==v],key=lambda r:int(r['trabalhadores'])) for v in VERSOES}
        series={v:rs for v,rs in series.items() if rs}
        if not series: ap.error(f'Nenhuma versão paralela para {entrada}')
        ps=sorted({int(r['trabalhadores']) for rs in series.values() for r in rs})
        titulo={'pequena':'1 MiB','media':'64 MiB','grande':'256 MiB'}.get(entrada,entrada)
        for chave,nome,ylabel,arquivo in [('total_mediana_s','Tempo de execução','Tempo mediano (s)','01_tempo'),('speedup','Speedup','Speedup (T serial / T paralelo)','02_speedup'),('eficiencia_pct','Eficiência','Eficiência (%)','03_eficiencia')]:
            fig,ax=plt.subplots(figsize=(9,5.2))
            for v,rs in series.items():
                ax.plot([int(r['trabalhadores']) for r in rs],[numero(r,chave) for r in rs],marker='o',label=NOMES[v])
            if chave=='total_mediana_s': ax.axhline(numero(serial,chave),linestyle='--',color='gray',label='Serial')
            elif chave=='speedup': ax.plot(ps,ps,linestyle='--',color='gray',label='Ideal')
            else: ax.axhline(100,linestyle='--',color='gray',label='Ideal')
            ax.set(title=f'{nome} — {titulo}',xlabel='Processos MPI / threads OpenMP',ylabel=ylabel,xticks=ps)
            ax.set_ylim(bottom=0); ax.grid(alpha=.25); ax.legend()
            salvar(fig,saida/f'{arquivo}_{entrada}.png')
        # Máximos independentes por fase: barras agrupadas, nunca empilhadas.
        mpi={v:rs for v,rs in series.items() if v!='openmp'}
        if mpi:
            fig,axes=plt.subplots(len(mpi),1,figsize=(10,3.5*len(mpi)),squeeze=False)
            for ax,(v,rs) in zip(axes[:,0],mpi.items()):
                if any(numero(r,k) is None for r in rs for k,_ in FASES):
                    plt.close(fig); ap.error(f'Fases ausentes para {entrada}/{v}. Execute o benchmark com os códigos instrumentados.')
                xs=list(range(len(rs))); largura=.25
                for j,(k,label) in enumerate(FASES):
                    ax.bar([x+(j-1)*largura for x in xs],[numero(r,k)*1000 for r in rs],width=largura,label=label)
                ax.set(title=NOMES[v],ylabel='Mediana (ms)',xlabel='Processos MPI',xticks=xs,xticklabels=[r['trabalhadores'] for r in rs]); ax.grid(axis='y',alpha=.25); ax.legend()
            fig.suptitle(f'Tempos por fase — {titulo}\nMáximos por rank medidos separadamente; não somar como tempo total')
            salvar(fig,saida/f'04_fases_{entrada}.png')
        if 'openmp' in series:
            # Comparação direta somente nos números de trabalhadores comuns.
            omp={int(r['trabalhadores']):numero(r,'total_mediana_s') for r in series['openmp']}
            comuns=sorted(set(omp).intersection(*(set(int(r['trabalhadores']) for r in rs) for rs in mpi.values()))) if mpi else []
            if comuns:
                fig,ax=plt.subplots(figsize=(9,5.2))
                for v,rs in mpi.items():
                    tempos={int(r['trabalhadores']):numero(r,'total_mediana_s') for r in rs}
                    ax.plot(comuns,[omp[p]/tempos[p] for p in comuns],marker='o',label=NOMES[v])
                ax.axhline(1,linestyle='--',color='gray',label='Mesmo tempo')
                ax.set(title=f'MPI em relação à melhor OpenMP — {titulo}',xlabel='Processos / threads',ylabel='T OpenMP / T MPI (> 1 favorece MPI)',xticks=comuns); ax.set_ylim(bottom=0); ax.grid(alpha=.25); ax.legend()
                salvar(fig,saida/f'05_comparacao_openmp_{entrada}.png')
        else:
            print(f'{entrada}: OpenMP ausente; comparação específica não gerada.')


if __name__=='__main__':
    main()
