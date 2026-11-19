#!/usr/bin/env python3
"""Benchmark OpenMP. Execute: python3 benchmark_openmp.py

Compila os executáveis nativos na pasta dos códigos (compatível com make clean).
No Docker, compila em diretório temporário para não sobrescrever os nativos.
Salva CSVs e um gráfico em resultados/. Não gera relatórios nem arquivos C.
"""

import csv
import hashlib
import os
import re
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SAIDA = ROOT / "resultados"
ENTRADA = ROOT / "entradas" / "grande.txt"  # 256 MiB
REPETICOES = 5
VERSOES = ["serial", "local", "manual", "reduction", "atomic", "ingenua", "critical"]
FLAGS = ["-std=c99", "-O2", "-fopenmp"]
COLUNAS = ["ambiente", "versao", "threads", "repeticao", "tempo_s", "status"]
TEMPO = re.compile(r"Execution time\s+([0-9.]+)\s+s")


def nome(versao):
    return "omp-letters" if versao == "serial" else f"omp-letters-{versao}"


def threads_testadas():
    maximo = int(os.getenv("BENCHMARK_MAX_THREADS") or subprocess.check_output(["nproc"]))
    return list(dict.fromkeys([1, 2, 4, 8, maximo]))


def executar(programa, threads, schedule=None):
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(threads)
    env["OMP_DYNAMIC"] = "FALSE"
    env.pop("OMP_SCHEDULE", None)
    if schedule:
        env["OMP_SCHEDULE"] = schedule

    with ENTRADA.open("rb") as arquivo:
        resultado = subprocess.run(
            [str(programa)], stdin=arquivo, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, timeout=300
        )
    erro = resultado.stderr.decode("utf-8", errors="replace")
    tempo = TEMPO.search(erro)
    if not tempo:
        raise RuntimeError(f"{programa.name} não informou o tempo: {erro}")
    return float(tempo.group(1)), hashlib.sha256(resultado.stdout).hexdigest(), resultado.returncode


def medir(ambiente):
    # Os executáveis nativos ficam ao lado dos .c e podem ser apagados por make clean.
    # No contêiner, usa /tmp para evitar sobrescrever os executáveis nativos
    # da pasta compartilhada entre host e Docker.
    pasta = ROOT if ambiente == "nativo" else Path("/tmp/openmp-benchmark-bin")
    if ambiente == "docker":
        pasta.mkdir(parents=True, exist_ok=True)
    tem_schedule = (ROOT / "omp-letters-schedule.c").is_file()
    versoes = VERSOES + (["schedule"] if tem_schedule else [])

    print(f"\n[{ambiente}] Compilando em {pasta}...", flush=True)
    for versao in versoes:
        fonte = ROOT / f"{nome(versao)}.c"
        if not fonte.is_file():
            raise FileNotFoundError(f"Faltando: {fonte.name}")
        subprocess.run(["gcc", *FLAGS, str(fonte), "-o", str(pasta / nome(versao))], check=True)

    # A saída da versão serial é a referência para comparar os histogramas.
    referencia = None
    arquivo_csv = SAIDA / f"medicoes_{ambiente}.csv"
    with arquivo_csv.open("w", newline="", encoding="utf-8") as arquivo:
        csv_writer = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        csv_writer.writeheader()

        def registrar(versao, p, repeticao, schedule=None):
            nonlocal referencia
            programa = pasta / nome("schedule" if schedule else versao)
            tempo, hash_saida, retorno = executar(programa, p, schedule)
            if referencia is None:
                if versao != "serial" or retorno != 0:
                    raise RuntimeError("A versão serial falhou")
                referencia = hash_saida
            correto = retorno == 0 and hash_saida == referencia
            status = "OK" if correto else ("CORRIDA" if versao == "ingenua" else "FALHA")
            csv_writer.writerow(dict(ambiente=ambiente, versao=versao, threads=p,
                                     repeticao=repeticao, tempo_s=tempo, status=status))
            arquivo.flush()
            print(f"  {versao:22s} {p:2d} threads | {repeticao}/{REPETICOES} | {tempo:.6f}s | {status}", flush=True)

        for versao in VERSOES:
            quantidades = [1] if versao == "serial" else threads_testadas()
            for p in quantidades:
                for repeticao in range(1, REPETICOES + 1):
                    registrar(versao, p, repeticao)

        # Usa o arquivo C que você já criou; não cria nem modifica código-fonte.
        if tem_schedule:
            for politica in ["static", "dynamic,1", "dynamic,1024"]:
                for repeticao in range(1, REPETICOES + 1):
                    registrar(f"schedule_{politica.replace(',', '_')}", 8, repeticao, politica)


def salvar_csv(caminho, campos, linhas):
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=campos)
        writer.writeheader()
        writer.writerows(linhas)


def resumir():
    grupos = {}
    for ambiente in ["nativo", "docker"]:
        with (SAIDA / f"medicoes_{ambiente}.csv").open(newline="", encoding="utf-8") as arquivo:
            for linha in csv.DictReader(arquivo):
                if linha["status"] == "OK":
                    chave = (ambiente, linha["versao"], int(linha["threads"]))
                    grupos.setdefault(chave, []).append(float(linha["tempo_s"]))

    medianas = {chave: statistics.median(tempos) for chave, tempos in grupos.items()}
    resumo = []
    for (ambiente, versao, p), tempos in sorted(grupos.items()):
        mediana = medianas[(ambiente, versao, p)]
        serial = medianas[(ambiente, "serial", 1)]
        speedup = serial / mediana
        resumo.append(dict(ambiente=ambiente, versao=versao, threads=p,
                           repeticoes=len(tempos), mediana_s=mediana,
                           speedup=speedup, eficiencia_percentual=100 * speedup / p))
    salvar_csv(SAIDA / "resumo.csv",
               ["ambiente", "versao", "threads", "repeticoes", "mediana_s", "speedup", "eficiencia_percentual"], resumo)

    comparacao = []
    for (ambiente, versao, p), tempo_nativo in sorted(medianas.items()):
        if ambiente != "nativo":
            continue
        tempo_docker = medianas.get(("docker", versao, p))
        if tempo_docker is not None:
            comparacao.append(dict(versao=versao, threads=p, nativo_s=tempo_nativo,
                                   docker_s=tempo_docker,
                                   diferenca_percentual=100 * (tempo_docker / tempo_nativo - 1)))
    salvar_csv(SAIDA / "comparacao_docker_nativo.csv",
               ["versao", "threads", "nativo_s", "docker_s", "diferenca_percentual"], comparacao)



def gerar_grafico():
    """Gráfico 1: tempo mediano por quantidade de threads, nativo e Docker."""
    import matplotlib
    matplotlib.use("Agg")  # Também funciona sem interface gráfica.
    import matplotlib.pyplot as plt

    with (SAIDA / "resumo.csv").open(newline="", encoding="utf-8") as arquivo:
        dados = list(csv.DictReader(arquivo))

    versoes = ["local", "manual", "reduction", "atomic", "critical"]
    fig, eixos = plt.subplots(1, 2, figsize=(13, 5.6), sharey=True)
    for eixo, ambiente in zip(eixos, ["nativo", "docker"]):
        serial = next(float(r["mediana_s"]) for r in dados
                      if r["ambiente"] == ambiente and r["versao"] == "serial")
        for versao in versoes:
            pares = sorted((int(r["threads"]), float(r["mediana_s"]))
                           for r in dados if r["ambiente"] == ambiente and r["versao"] == versao)
            if pares:
                eixo.plot([p for p, _ in pares], [t for _, t in pares],
                          marker="o", linewidth=2, label=versao.capitalize())
        eixo.axhline(serial, color="black", linestyle="--", linewidth=1.5,
                     label="Serial (referência)")
        eixo.set_title("Linux nativo" if ambiente == "nativo" else "Docker")
        eixo.set_xlabel("Quantidade de threads")
        eixo.set_xticks(sorted({int(r["threads"]) for r in dados
                                if r["ambiente"] == ambiente and r["versao"] in versoes}))
        eixo.set_yscale("log")  # Critical é muito mais lenta: escala log permite ver todas.
        eixo.grid(True, which="both", alpha=0.25)
    eixos[0].set_ylabel("Tempo mediano (segundos) — escala log")
    linhas, rotulos = eixos[0].get_legend_handles_labels()
    fig.legend(linhas, rotulos, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.035))
    fig.suptitle("Tempo de execução × quantidade de threads")
    fig.text(0.5, 0.005, "Ingênua omitida: pode produzir resultados incorretos.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.12, 1, 0.93))
    destino = SAIDA / "tempo_por_threads.png"
    fig.savefig(destino, dpi=170)
    plt.close(fig)
    print(f"Gráfico gerado: {destino}")


def main():
    SAIDA.mkdir(exist_ok=True)
    if os.getenv("BENCHMARK_DOCKER") == "1":
        medir("docker")
        return

    if not all((ROOT / "entradas" / n).exists() for n in ["pequena.txt", "media.txt", "grande.txt"]):
        subprocess.run(["make", "entradas"], cwd=ROOT, check=True)
    subprocess.run(["sha256sum", "-c", "entradas.sha256"], cwd=ROOT, check=True)

    medir("nativo")
    print("\n[docker] Preparando imagem e executando os mesmos testes...", flush=True)
    subprocess.run(["docker", "build", "-t", "openmp-benchmark", "."], cwd=ROOT, check=True)
    subprocess.run([
        "docker", "run", "--rm", "-i", "--user", f"{os.getuid()}:{os.getgid()}",
        "-v", f"{ROOT}:/lettes", "-w", "/lettes",
        "-e", "BENCHMARK_DOCKER=1",
        "-e", f"BENCHMARK_MAX_THREADS={threads_testadas()[-1]}",
        "openmp-benchmark", "python3", "benchmark_openmp.py"
    ], check=True)
    resumir()
    gerar_grafico()
    print("\nConcluído. Executáveis nativos na raiz (make clean os remove).")
    print("CSVs e gráfico em resultados/; binários Docker ficam só no contêiner.")


if __name__ == "__main__":
    main()
