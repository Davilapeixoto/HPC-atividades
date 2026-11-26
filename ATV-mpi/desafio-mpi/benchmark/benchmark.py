#!/usr/bin/env python3
"""Benchmark MPI do desafio HPC. Execute na raiz do projeto, dentro do contêiner."""
import argparse
import csv
import hashlib
import os
import re
import shlex
import shutil
import statistics as stats
import subprocess
from pathlib import Path

VERSOES = ('coletivas', 'p2p', 'allreduce')
NUM = r'([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?\d+)?)'
TEMPO = re.compile(r'Execution time\s+' + NUM + r'\s*s', re.I)
FASES = re.compile(r'Phases\s+' + NUM + r'\s+' + NUM + r'\s+' + NUM + r'\s*s', re.I)


def cpus_disponiveis():
    # Conta os pares (socket, core) apenas entre as CPUs permitidas ao processo.
    permitidas = os.sched_getaffinity(0)
    nucleos = set()
    try:
        for cpu in permitidas:
            topo = Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
            socket = (topo/'physical_package_id').read_text().strip()
            core = (topo/'core_id').read_text().strip()
            if int(socket) < 0 or int(core) < 0:
                raise ValueError('topologia desconhecida')
            nucleos.add((socket, core))
    except (OSError, ValueError):
        nucleos.clear()
    return len(nucleos) or None, len(permitidas)


def csv_write(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def executar(cmd, arquivo, env, timeout):
    if arquivo is None:
        return subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True,
                              env=env, timeout=timeout)
    with arquivo.open('rb') as f:
        return subprocess.run(cmd, stdin=f, capture_output=True, env=env, timeout=timeout)


def medir(stderr):
    total = TEMPO.search(stderr)
    fases = FASES.search(stderr)
    return (float(total[1]) if total else None,
            tuple(map(float, fases.groups())) if fases else (None, None, None))


def flags_padrao(p, fisicos, logicos):
    if p <= fisicos:
        return []
    if p <= logicos:
        return ['--use-hwthread-cpus']
    return ['--use-hwthread-cpus', '--oversubscribe']


def salvar_investigacao(out, nome, cmd, env, timeout, arquivo=None):
    # Apenas as investigações têm arquivos de saída individuais.
    caminho = out/f'{nome}.txt'
    comando = shlex.join(cmd)
    if arquivo is not None:
        comando += ' < '+shlex.quote(str(arquivo))+' > /dev/null'
    with caminho.open('w', encoding='utf-8') as f:
        f.write('$ '+comando+'\n\n')
        f.flush()
        try:
            if arquivo is None:
                r = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=f,
                                   stderr=subprocess.STDOUT, env=env, timeout=timeout)
            else:
                with arquivo.open('rb') as entrada:
                    r = subprocess.run(cmd, stdin=entrada, stdout=subprocess.DEVNULL,
                                       stderr=f, env=env, timeout=timeout)
            f.write(f'\nCódigo de saída: {r.returncode}\n')
            f.flush()
            saida = caminho.read_text(encoding='utf-8', errors='replace').lower()
            if r.returncode == 0:
                status = 'OK'
            elif 'not enough slots' in saida:
                status = 'SEM_SLOTS'
            else:
                status = 'FALHA (veja a saída)'
        except subprocess.TimeoutExpired:
            f.write(f'\nTempo limite de {timeout} s excedido.\n')
            status = 'TIMEOUT'
        except OSError as e:
            f.write(f'\nErro ao executar: {e}\n')
            status = 'FALHA (veja a saída)'
        f.write(f'Resultado: {status}\n')
    print(f'Investigação {nome}: {status}', flush=True)
    return status


def testar_slots(out, fisicos, ambiente, env, timeout):
    out.mkdir(parents=True, exist_ok=True)
    dentro = salvar_investigacao(out, f'{ambiente}_slots_{fisicos}',
                                 ['mpirun','-np',str(fisicos),'hostname'], env, timeout)
    acima = salvar_investigacao(out, f'{ambiente}_slots_{fisicos+1}',
                                ['mpirun','-np',str(fisicos+1),'hostname'], env, timeout)
    if dentro == 'OK' and acima == 'SEM_SLOTS':
        print(f'Limite padrão observado: {fisicos} slots.', flush=True)


def investigar(out, fisicos, logicos, ambiente, env, timeout):
    out.mkdir(parents=True, exist_ok=True)
    arquivo = Path('entradas/grande.txt')
    exe = './mpi-letters-coletivas'
    testes = [
        ('afinidade_2', ['--report-bindings'], 2),
        ('afinidade_4', ['--report-bindings'], 4),
        ('afinidade_core_2', ['--report-bindings','--bind-to','core'], 2),
        ('afinidade_core_4', ['--report-bindings','--bind-to','core'], 4),
        ('acima_fisicos_hwthreads', ['--use-hwthread-cpus'], max(fisicos+1,logicos)),
        ('acima_logicos_oversubscribe', ['--use-hwthread-cpus','--oversubscribe'], logicos+1),
    ]
    for nome, flags, p in testes:
        cmd = ['mpirun', *flags, '-np', str(p), exe]
        salvar_investigacao(out, nome, cmd, env, timeout, arquivo)
    testar_slots(out, fisicos, ambiente, env, timeout)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repeticoes', type=int, default=5)
    ap.add_argument('--processos', nargs='+', type=int, help='Padrão: 1, 2, 4, 8, físicos e lógicos')
    ap.add_argument('--fisicos', type=int, help='Substitui a detecção de núcleos físicos disponíveis')
    ap.add_argument('--logicos', type=int, help='Substitui a detecção de CPUs lógicas disponíveis')
    ap.add_argument('--entradas', nargs='+', choices=['pequena','media','grande'], default=['grande'])
    ap.add_argument('--mpi-args', default=None, help='Substitui as flags automáticas do benchmark principal; use --mpi-args="" para nenhuma')
    ap.add_argument('--timeout', type=int, default=300)
    ap.add_argument('--aquecimentos', type=int, default=0)
    ap.add_argument('--exigir-fases', action='store_true', help='Compatibilidade com o script anterior: fases já são obrigatórias')
    ap.add_argument('--ambiente', choices=['nativo','container'], help='Identifica o ambiente da medição')
    modos = ap.add_mutually_exclusive_group()
    modos.add_argument('--apenas-investigacoes', action='store_true', help='Executa as investigações sem repetir o benchmark')
    modos.add_argument('--apenas-slots', action='store_true', help='Verifica os slots padrão, inclusive no Linux nativo, sem precisar dos executáveis do desafio')
    args = ap.parse_args()
    fisicos_detectados, logicos_detectados = cpus_disponiveis()
    fisicos = args.fisicos if args.fisicos is not None else fisicos_detectados
    logicos = args.logicos if args.logicos is not None else logicos_detectados
    if fisicos is None:
        ap.error('Não foi possível detectar núcleos físicos. Consulte lscpu e informe --fisicos N.')
    if not (1 <= fisicos <= logicos) or args.repeticoes < 5 or args.aquecimentos < 0 or args.timeout < 1:
        ap.error('Repetições >= 5, aquecimentos >= 0, timeout positivo e 1 <= físicos <= lógicos.')
    ps = sorted(set(args.processos or [1,2,4,8,fisicos,logicos]))
    if min(ps) < 1:
        ap.error('Processos devem ser positivos.')
    entradas = list(dict.fromkeys(args.entradas))
    root = Path.cwd()
    out = root/'resultados'
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LC_ALL='C')
    ambiente = args.ambiente or ('container' if Path('/.dockerenv').exists() or Path('/run/.containerenv').exists() or os.getenv('APPTAINER_CONTAINER') or os.getenv('SINGULARITY_CONTAINER') else 'nativo')
    if not shutil.which('mpirun'):
        ap.error('mpirun não encontrado neste ambiente.')
    pasta_investigacoes = out/'investigacoes'
    if args.apenas_slots:
        testar_slots(pasta_investigacoes, fisicos, ambiente, env, args.timeout)
        print(f'\nInvestigações: {pasta_investigacoes}')
        return
    if args.apenas_investigacoes:
        if not os.access(root/'mpi-letters-coletivas', os.X_OK) or not (root/'entradas'/'grande.txt').is_file():
            ap.error('As investigações precisam de mpi-letters-coletivas e entradas/grande.txt.')
        investigar(pasta_investigacoes, fisicos, logicos, ambiente, env, args.timeout)
        print(f'\nInvestigações: {pasta_investigacoes}')
        return
    flags = shlex.split(args.mpi_args) if args.mpi_args is not None else None
    def mpi_flags(p):
        return flags if flags is not None else flags_padrao(p, fisicos, logicos)
    serial = root/'mpi-letters'
    if not serial.is_file():
        serial = root/'letters'
    bins = {v:root/f'mpi-letters-{v}' for v in VERSOES}
    for exe in [serial, *bins.values()]:
        if not exe.is_file() or not os.access(exe, os.X_OK):
            ap.error(f'Executável não encontrado ou sem permissão: {exe}')
    arquivos = {e:root/'entradas'/f'{e}.txt' for e in ('pequena','media','grande')}
    for arquivo in arquivos.values():
        if not arquivo.is_file():
            ap.error(f'Entrada não encontrada: {arquivo}. Execute make entradas.')
    for nome in ('resumo.csv','tempos_brutos.csv','corretude.csv'):
        (out/nome).unlink(missing_ok=True)
    print(f'CPU: {fisicos} núcleos físicos acessíveis, {logicos} CPUs lógicas. Testes: {ps}', flush=True)
    with (out/'ambiente.txt').open('w', encoding='utf-8') as f:
        f.write(f'Ambiente: {ambiente}\nNucleos fisicos acessiveis: {fisicos}\nCPUs logicas acessiveis: {logicos}\nProcessos: {ps}\nRepeticoes: {args.repeticoes}\nAquecimentos: {args.aquecimentos}\nExecutaveis pre-compilados; flags de compilacao nao verificadas pelo script.\n')
        for p in ps:
            f.write(f'MPI flags p={p}: {shlex.join(mpi_flags(p)) or "(nenhuma)"}\n')
        for cmd in [['lscpu'],['free','-h'],['uname','-a'],['cat','/etc/os-release'],['gcc','--version'],['mpicc','--showme'],['mpirun','--version'],['sha256sum','-c','entradas.sha256']]:
            f.write('\n$ '+shlex.join(cmd)+'\n'); f.flush()
            try:
                r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, timeout=args.timeout)
            except FileNotFoundError:
                f.write('Comando indisponível.\n')
                if cmd[0]=='sha256sum': raise
                continue
            if cmd[0]=='sha256sum' and r.returncode:
                raise RuntimeError('SHA-256 das entradas falhou')
        for path in ['/proc/self/status','/sys/fs/cgroup/cpu.max','/sys/fs/cgroup/cpuset.cpus.effective','/sys/fs/cgroup/memory.max']:
            p = Path(path)
            if p.exists():
                content = p.read_text()
                if path.endswith('/status'):
                    content = '\n'.join(x for x in content.splitlines() if x.startswith(('Cpus_allowed_list:', 'Mems_allowed_list:')))
                f.write(f'\n{path}:\n{content}\n')

    # Corretude: entradas pequena, media e casos extremos.
    arquivos['vazio'] = root/'entradas'/'vazio.txt'
    arquivos['tres'] = root/'entradas'/'tres.txt'
    for nome, conteudo in [('vazio', b''), ('tres', b'abc')]:
        if not arquivos[nome].is_file():
            arquivos[nome].write_bytes(conteudo)
        elif arquivos[nome].read_bytes() != conteudo:
            raise RuntimeError(f'Conteúdo inesperado em {arquivos[nome]}')
    testes = {nome:arquivos[nome] for nome in ('pequena','media','vazio','tres')}
    corretude = []
    for nome, arquivo in testes.items():
        base = executar([str(serial)], arquivo, env, args.timeout)
        if base.returncode:
            raise RuntimeError(f'Serial falhou: {nome}\n{base.stderr.decode(errors="replace")}')
        processos = sorted({1,2,3,4,8,fisicos}) if nome in ('pequena','media') else [1,8]
        for v in VERSOES:
            for p in processos:
                cmd = ['mpirun', *mpi_flags(p), '-np', str(p), str(bins[v])]
                r = executar(cmd, arquivo, env, args.timeout)
                ok = r.returncode == 0 and r.stdout == base.stdout
                corretude.append(dict(entrada=nome,versao=v,trabalhadores=p,resultado='OK' if ok else 'FALHA',sha256_serial=hashlib.sha256(base.stdout).hexdigest(),sha256_mpi=hashlib.sha256(r.stdout).hexdigest(),mpi_args=shlex.join(mpi_flags(p))))
                csv_write(out/'corretude.csv', corretude)
                print(f'Corretude {nome:7} {v:10} p={p:2}: {"OK" if ok else "FALHA"}', flush=True)
                if not ok:
                    raise RuntimeError(f'Histograma diferente ou falha MPI: {nome} {v} p={p}\n'
                                       f'{r.stderr.decode(errors="replace")}')

    # Benchmark principal: tempos internos, mediana.
    configs = [('serial',1)] + [(v,p) for v in VERSOES for p in ps]
    dados = []
    for entrada in entradas:
        arquivo = arquivos[entrada]
        base = None
        for v,p in configs:
            for rep in range(1-args.aquecimentos, args.repeticoes+1):
                e = env.copy()
                if v=='serial':
                    cmd = [str(serial)]
                else:
                    cmd = ['mpirun', *mpi_flags(p), '-np', str(p), str(bins[v])]
                label = f'{entrada}_{v}_{p}_{rep}'
                r = executar(cmd, arquivo, e, args.timeout)
                if base is None and v=='serial' and r.returncode==0:
                    base = r.stdout
                if r.returncode or r.stdout != base:
                    raise RuntimeError(f'Execucao falhou ou histograma diferente: {label}\n'
                                       f'{r.stderr.decode(errors="replace")}')
                t,(d,c,b) = medir(r.stderr.decode(errors='replace'))
                if t is None or t<=0 or (v in VERSOES and d is None):
                    raise RuntimeError(f'Tempos ausentes ou inválidos: {label}\n{r.stderr.decode(errors="replace")}')
                if v=='serial': c=t
                print(f'{entrada:7} {v:10} {p:2} trabalhadores | {rep}/{args.repeticoes} | {t:.6f}s | OK', flush=True)
                if rep>0:
                    dados.append(dict(entrada=entrada,bytes=arquivo.stat().st_size,versao=v,trabalhadores=p,repeticao=rep,distribuir_s=d,contar_s=c,combinar_s=b,total_s=t,mpi_args=shlex.join(mpi_flags(p)) if v in VERSOES else ''))
                    csv_write(out/'tempos_brutos.csv', dados)
    resumo=[]
    for entrada in entradas:
        ref=stats.median(x['total_s'] for x in dados if x['entrada']==entrada and x['versao']=='serial')
        for v,p in configs:
            grupo=[x for x in dados if x['entrada']==entrada and x['versao']==v and x['trabalhadores']==p]
            def med(chave):
                vals=[x[chave] for x in grupo if x[chave] is not None]
                return round(stats.median(vals),9) if vals else None
            t=stats.median(x['total_s'] for x in grupo)
            sp=ref/t
            resumo.append(dict(entrada=entrada,versao=v,trabalhadores=p,repeticoes=len(grupo),distribuir_mediana_s=med('distribuir_s'),contar_mediana_s=med('contar_s'),combinar_mediana_s=med('combinar_s'),total_mediana_s=round(t,9),total_desvio_padrao_s=round(stats.stdev(x['total_s'] for x in grupo),9),speedup=round(sp,6),eficiencia_pct=round(100*sp/p,4)))
    csv_write(out/'resumo.csv',resumo)
    for row in resumo:
        print(f"{row['entrada']:7} {row['versao']:10} p={row['trabalhadores']:2} T={row['total_mediana_s']:.6f}s S={row['speedup']:.3f} E={row['eficiencia_pct']:.2f}%")

    investigar(pasta_investigacoes, fisicos, logicos, ambiente, env, args.timeout)
    print(f'\nResultados: {out}')


if __name__=='__main__':
    main()
