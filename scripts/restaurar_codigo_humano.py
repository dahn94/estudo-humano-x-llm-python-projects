"""Restaura o código humano de referência a partir do commit registrado.

Os snapshots humanos não são versionados: são reconstruídos do GitHub pelo SHA
gravado em `configuracao/`. Este script só baixa o código (sparse checkout dos
mesmos padrões usados no estudo); não executa Semgrep nem SonarQube.

Uso:
    python scripts/restaurar_codigo_humano.py            # os 16 finalistas
    python scripts/restaurar_codigo_humano.py --todos    # os 50 candidatos
    python scripts/restaurar_codigo_humano.py psf/requests
"""
from __future__ import annotations

import argparse
import sys

import yaml

from processar_50_humanos import ROOT, preparar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repos", nargs="*", help="nomes proprietario/repositorio; vazio = os 16 finalistas")
    parser.add_argument("--todos", action="store_true", help="restaura os 50 candidatos")
    args = parser.parse_args()

    todos = yaml.safe_load((ROOT / "configuracao" / "repositorios.yaml").read_text(encoding="utf-8"))["repositorios"]
    finalistas = yaml.safe_load((ROOT / "configuracao" / "repositorios_16_finalistas.yaml").read_text(encoding="utf-8"))["finalistas"]

    if args.todos:
        alvo = {r["nome"] for r in todos}
    elif args.repos:
        alvo = set(args.repos)
    else:
        alvo = {r["nome"] for r in finalistas}

    selecionados = [r for r in todos if r["nome"] in alvo]
    faltando = alvo - {r["nome"] for r in selecionados}
    if faltando:
        sys.exit(f"Não cadastrados em configuracao/repositorios.yaml: {', '.join(sorted(faltando))}")

    for i, repo in enumerate(selecionados, 1):
        print(f"[{i}/{len(selecionados)}] {repo['nome']} @ {repo['commit'][:12]}", flush=True)
        destino = preparar(repo)
        print(f"    -> {destino.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
