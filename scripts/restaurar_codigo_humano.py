"""Restaura o código humano de referência a partir do commit registrado.

Os snapshots humanos não são versionados: são reconstruídos do GitHub pelo SHA
gravado em `configuracao/repositorios.yaml`.

Uso:
    uv run scripts/restaurar_codigo_humano.py            # os 16 finalistas
    uv run scripts/restaurar_codigo_humano.py --todos    # os 50 candidatos
    uv run scripts/restaurar_codigo_humano.py psf/requests
"""
from __future__ import annotations

import argparse

from comum import ROOT, preparar, selecionar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repos", nargs="*", help="dono/repo ou slug; vazio = os 16 finalistas")
    parser.add_argument("--todos", action="store_true", help="restaura os 50 candidatos")
    args = parser.parse_args()

    repos = selecionar(args.repos, args.todos)
    for i, repo in enumerate(repos, 1):
        print(f"[{i}/{len(repos)}] {repo['nome']} @ {repo['commit'][:12]}", flush=True)
        print(f"    -> {preparar(repo).relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
