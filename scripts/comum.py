"""Caminhos, cadastro dos repositórios e restauração do snapshot humano."""
from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ORIGENS = ("humano", "openai", "gemini", "claude")
IGNORADOS = {".git", ".venv", "venv", "node_modules", "vendor", "vendors", "third_party", "third-party", "build", "dist", "__pycache__"}

# Arquivos baixados do snapshot humano: código Python e documentação pública.
PADROES_SPARSE = ["*.py", "README*", "docs/**/*.md", "docs/**/*.rst", "*.md", "*.rst", "pyproject.toml", "setup.py", "setup.cfg", "requirements*.txt", "Pipfile", "tox.ini"]


def candidatos() -> list[dict]:
    """Os 50 candidatos, com SHA e data do commit de corte."""
    return yaml.safe_load((ROOT / "configuracao" / "repositorios.yaml").read_text(encoding="utf-8"))["repositorios"]


def finalistas() -> list[dict]:
    """Os 16 repositórios analisados no artigo, com os dados completos do cadastro."""
    nomes = {r["nome"] for r in yaml.safe_load((ROOT / "configuracao" / "repositorios_16_finalistas.yaml").read_text(encoding="utf-8"))["finalistas"]}
    return [r for r in candidatos() if r["nome"] in nomes]


def selecionar(nomes: list[str], todos: bool = False) -> list[dict]:
    """Nomes `dono/repo` ou slugs; vazio = finalistas; `todos` = 50 candidatos."""
    if todos:
        return candidatos()
    if not nomes:
        return finalistas()
    pedidos = {n.replace("__", "/") for n in nomes}
    achados = [r for r in candidatos() if r["nome"] in pedidos]
    faltando = pedidos - {r["nome"] for r in achados}
    if faltando:
        raise SystemExit(f"Não cadastrados em configuracao/repositorios.yaml: {', '.join(sorted(faltando))}")
    return achados


def git(args: list[str], cwd: Path) -> None:
    proc = subprocess.run(["git", "-c", "core.longpaths=true", *args], cwd=cwd, text=True, capture_output=True, timeout=1800)
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout)[-4000:])


def preparar(repo: dict) -> Path:
    """Baixa o snapshot humano no commit de corte (fetch raso + sparse checkout)."""
    destino = ROOT / "projetos" / repo["slug"] / "humano"
    destino.mkdir(parents=True, exist_ok=True)
    if not (destino / ".git").exists():
        git(["init", "-q"], destino)
        git(["remote", "add", "origin", repo["github"] + ".git"], destino)
    git(["fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", repo["commit"]], destino)
    git(["sparse-checkout", "set", "--no-cone", *PADROES_SPARSE], destino)
    git(["checkout", "-q", "--force", "--detach", "FETCH_HEAD"], destino)
    return destino
