"""Roda Semgrep e SonarQube (em Docker) sobre uma ou mais origens de código.

Mesma configuração para as quatro origens: só arquivos .py, sem ambientes
virtuais, vendorizados, builds ou gerados; regras em configuracao/semgrep-regras.yaml;
SonarQube com o perfil Sonar way.

Saída: dados_brutos/{semgrep,sonarqube}/<slug>/<origem>.json e logs em
resultados/<origem>/<slug>/logs_tecnicos/. Um JSON que já existe não é refeito
sem --refazer.

Uso:
    uv run scripts/sonarqube.py preparar                  # uma vez
    uv run scripts/analisar.py                            # 16 finalistas, 4 origens
    uv run scripts/analisar.py psf/requests --origem claude
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

import sonarqube
from comum import IGNORADOS, ORIGENS, ROOT, selecionar

TRABALHO = ROOT / ".trabalho"
EXCLUSOES_SONAR = "**/.git/**,**/.venv/**,**/venv/**,**/vendor/**,**/vendors/**,**/third_party/**,**/node_modules/**,**/build/**,**/dist/**"


def preparar_copia(origem_dir: Path, destino: Path) -> int:
    """Copia só os .py analisáveis para uma pasta limpa; devolve quantos."""
    if destino.exists():
        shutil.rmtree(destino)
    n = 0
    for arquivo in origem_dir.rglob("*.py"):
        relativo = arquivo.relative_to(origem_dir)
        if set(relativo.parts[:-1]) & IGNORADOS or not arquivo.is_file():
            continue
        alvo = destino / relativo
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(arquivo, alvo)
        n += 1
    return n


def compose_run(servico: str, copia: Path, *args: str) -> subprocess.CompletedProcess[str]:
    montagem = "/src" if servico == "semgrep" else "/usr/src"
    return subprocess.run(
        ["docker", "compose", "run", "--rm", "-T", "-v", f"{copia}:{montagem}", servico, *args],
        cwd=ROOT, text=True, capture_output=True,
    )


def semgrep(copia: Path, saida: Path, logs: Path) -> None:
    proc = compose_run(
        "semgrep", copia, "semgrep", "scan",
        "--config", "/regras/semgrep-regras.yaml",
        "--json", "--metrics", "off", "--timeout", "30", "--timeout-threshold", "5", ".",
    )
    (logs / "semgrep.stderr.log").write_text(proc.stderr, encoding="utf-8")
    (logs / "semgrep_exit_code.txt").write_text(f"{proc.returncode}\n")
    json.loads(proc.stdout)  # falha aqui se o Semgrep não devolveu JSON
    saida.write_text(proc.stdout, encoding="utf-8")


def sonar(copia: Path, chave: str, nome: str, saida: Path, logs: Path, tok: str) -> None:
    proc = compose_run(
        "scanner", copia,
        f"-Dsonar.projectKey={chave}", f"-Dsonar.projectName={nome}",
        f"-Dsonar.token={tok}",
        "-Dsonar.sources=.", "-Dsonar.inclusions=**/*.py", f"-Dsonar.exclusions={EXCLUSOES_SONAR}",
        "-Dsonar.sourceEncoding=UTF-8", "-Dsonar.python.version=3",
    )
    (logs / "sonarqube_scanner.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"sonar-scanner saiu com {proc.returncode}; veja {logs / 'sonarqube_scanner.log'}")
    achado = re.search(r"api/ce/task\?id=([\w-]+)", proc.stdout)
    if not achado:
        raise RuntimeError(f"ID da tarefa não encontrado; veja {logs / 'sonarqube_scanner.log'}")
    ce_task = achado.group(1)
    sonarqube.aguardar_tarefa(ce_task, tok)
    saida.write_text(json.dumps(sonarqube.coletar(chave, tok), ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repos", nargs="*", help="dono/repo ou slug; vazio = os 16 finalistas")
    parser.add_argument("--todos", action="store_true", help="os 50 candidatos")
    parser.add_argument("--origem", choices=ORIGENS, action="append", help="repetível; padrão = todas")
    parser.add_argument("--ferramenta", choices=("semgrep", "sonarqube"), action="append", help="padrão = ambas")
    parser.add_argument("--refazer", action="store_true", help="sobrescreve JSONs existentes")
    args = parser.parse_args()
    origens = args.origem or list(ORIGENS)
    ferramentas = args.ferramenta or ["semgrep", "sonarqube"]

    tok = None
    if "sonarqube" in ferramentas:
        sonarqube.aguardar(30)
        tok = sonarqube.token()

    for repo in selecionar(args.repos, args.todos):
        slug = repo["slug"]
        for origem in origens:
            fonte = ROOT / "projetos" / slug / origem
            copia = TRABALHO / f"{slug}__{origem}"
            n = preparar_copia(fonte, copia) if fonte.exists() else 0
            if not n:
                print(f"-- {slug}/{origem}: sem arquivos .py, pulando")
                continue
            logs = ROOT / "resultados" / origem / slug / "logs_tecnicos"
            logs.mkdir(parents=True, exist_ok=True)
            prefixo = "human" if origem == "humano" else origem
            chave = f"{prefixo}-" + re.sub(r"[^a-z0-9_-]", "-", slug.lower())[:180]
            for ferramenta in ferramentas:
                saida = ROOT / "dados_brutos" / ferramenta / slug / f"{origem}.json"
                if saida.exists() and not args.refazer:
                    print(f"== {slug}/{origem}/{ferramenta}: já existe")
                    continue
                saida.parent.mkdir(parents=True, exist_ok=True)
                print(f">> {slug}/{origem}/{ferramenta} ({n} arquivos .py)", flush=True)
                if ferramenta == "semgrep":
                    semgrep(copia, saida, logs)
                else:
                    sonar(copia, chave, f"{origem} - {slug}", saida, logs, tok)
            shutil.rmtree(copia, ignore_errors=True)


if __name__ == "__main__":
    main()
