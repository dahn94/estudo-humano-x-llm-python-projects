from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml


ROOT = Path(__file__).resolve().parent.parent
CUTOFF = "2020-12-31"
QUANTIDADE = 50
MINIMO_LINHAS_PYTHON = 500

# Exclusoes metodologicas verificadas manualmente na classificacao inicial.
# Esses itens sao listas, livros, cursos, colecoes de links/dados ou material
# predominantemente educacional, e nao sistemas Python comparaveis.
RANKS_EXCLUIDOS = {
    1, 2, 3, 4, 5, 8, 19, 20, 21, 22, 28, 29, 32, 46, 49, 50,
    62, 64, 66, 69, 71, 75, 77, 81, 90, 93, 96, 98, 99,
}


def cabecalhos() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "python-prellm-research",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def ultimo_commit_antes_do_corte(repo: str) -> tuple[str, str]:
    resposta = requests.get(
        f"https://api.github.com/repos/{repo}/commits",
        params={"until": f"{CUTOFF}T23:59:59Z", "per_page": 1},
        headers=cabecalhos(),
        timeout=45,
    )
    resposta.raise_for_status()
    commits = resposta.json()
    if not commits:
        raise RuntimeError(f"{repo}: nenhum commit encontrado antes de {CUTOFF}")
    commit = commits[0]
    return commit["sha"], commit["commit"]["committer"]["date"]


def executar_git(args: list[str], cwd: Path) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def contar_linhas_python(repo: str, sha: str) -> tuple[int, int]:
    ignorar = {
        ".git", ".venv", "venv", "node_modules", "vendor", "vendors",
        "third_party", "third-party", "build", "dist", "__pycache__",
    }
    with tempfile.TemporaryDirectory(prefix="prellm_loc_") as temporario:
        destino = Path(temporario)
        executar_git(["init"], destino)
        executar_git(["remote", "add", "origin", f"https://github.com/{repo}.git"], destino)
        executar_git(
            ["-c", "protocol.version=2", "fetch", "--depth", "1", "--filter=blob:none", "origin", sha],
            destino,
        )
        executar_git(["sparse-checkout", "init", "--no-cone"], destino)
        executar_git(["sparse-checkout", "set", "--no-cone", "*.py"], destino)
        executar_git(["checkout", "--detach", "FETCH_HEAD"], destino)

        arquivos = 0
        linhas = 0
        for arquivo in destino.rglob("*.py"):
            partes = {parte.lower() for parte in arquivo.relative_to(destino).parts}
            if partes & ignorar:
                continue
            try:
                conteudo = arquivo.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            arquivos += 1
            linhas += sum(1 for linha in conteudo.splitlines() if linha.strip())
        return arquivos, linhas


def main() -> None:
    bruto_path = ROOT / "configuracao" / "github_top100_raw.json"
    itens = json.loads(bruto_path.read_text(encoding="utf-8"))["items"]
    config_atual_path = ROOT / "configuracao" / "repositorios.yaml"
    config_atual = yaml.safe_load(config_atual_path.read_text(encoding="utf-8"))
    commits_cache = {
        repo["nome"]: (repo.get("commit", ""), repo.get("commit_date", ""))
        for repo in config_atual.get("repositorios", [])
    }
    loc_cache_path = ROOT / "configuracao" / "cache_loc_python.json"
    loc_cache = (
        json.loads(loc_cache_path.read_text(encoding="utf-8"))
        if loc_cache_path.exists()
        else {}
    )

    selecionados = []
    auditoria = []
    for rank, item in enumerate(itens, 1):
        motivo = ""
        if rank in RANKS_EXCLUIDOS:
            motivo = "nao e projeto de software comparavel"
        elif len(selecionados) >= QUANTIDADE:
            motivo = "fora das 50 primeiras posicoes elegiveis"
        else:
            nome = item["full_name"]
            print(f"[{len(selecionados) + 1:02d}/50] Medindo LOC no commit de corte: {nome}", flush=True)
            sha, data_commit = commits_cache.get(nome, ("", ""))
            if not sha:
                sha, data_commit = ultimo_commit_antes_do_corte(nome)
            chave_cache = f"{nome}@{sha}"
            try:
                if chave_cache in loc_cache:
                    arquivos_python = loc_cache[chave_cache]["arquivos_python"]
                    linhas_python = loc_cache[chave_cache]["python_loc"]
                else:
                    arquivos_python, linhas_python = contar_linhas_python(nome, sha)
                    loc_cache[chave_cache] = {
                        "arquivos_python": arquivos_python,
                        "python_loc": linhas_python,
                    }
                    loc_cache_path.write_text(
                        json.dumps(loc_cache, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
            except subprocess.CalledProcessError as erro:
                detalhe = (erro.stderr or "falha no checkout").strip().replace("\n", " ")
                motivo = f"falha ao medir LOC: {detalhe[:180]}"
                arquivos_python = 0
                linhas_python = 0
            if not motivo and linhas_python < MINIMO_LINHAS_PYTHON:
                motivo = f"menos de {MINIMO_LINHAS_PYTHON} linhas Python no commit de corte"
            if not motivo:
                selecionados.append({
                    "nome": nome,
                    "slug": nome.replace("/", "__"),
                    "github": item["html_url"],
                    "commit": sha,
                    "commit_date": data_commit,
                    "grupo": "amostra_popular",
                    "rank_gitstar": rank,
                    "stars_na_coleta": item["stargazers_count"],
                    "github_size_kb": item["size"],
                    "arquivos_python": arquivos_python,
                    "python_loc_aproximada": linhas_python,
                })
        auditoria.append({
            "rank_gitstar": rank,
            "repositorio": item["full_name"],
            "estrelas": item["stargazers_count"],
            "tamanho_kb": item["size"],
            "arquivos_python": locals().get("arquivos_python", "") if not motivo.startswith("nao e") else "",
            "python_loc": locals().get("linhas_python", "") if not motivo.startswith("nao e") else "",
            "incluido": "sim" if not motivo else "nao",
            "motivo_exclusao": motivo,
        })
        arquivos_python = ""
        linhas_python = ""

    if len(selecionados) != QUANTIDADE:
        raise RuntimeError(f"Esperados 50 candidatos, encontrados {len(selecionados)}")

    data_coleta = datetime.now(timezone.utc).isoformat()
    configuracao = {
        "cutoff_date": CUTOFF,
        "quantidade_planejada": QUANTIDADE,
        "quantidade_selecionada": len(selecionados),
        "data_coleta_gitstar_utc": data_coleta,
        "criterios_selecao": {
            "linguagem_principal": "Python",
            "ordenacao": "estrelas_decrescente",
            "fork": False,
            "arquivado": False,
            "criado_antes_de": "2021-01-01",
            "commit_obrigatorio_antes_do_corte": True,
            "somente_software_executavel": True,
            "minimo_linhas_python_nao_vazias": MINIMO_LINHAS_PYTHON,
            "tamanho_github_usado_apenas_como_dado_descritivo": True,
        },
        "repositorios": selecionados,
    }
    yaml_texto = yaml.safe_dump(configuracao, allow_unicode=True, sort_keys=False)
    (ROOT / "configuracao" / "repositorios.yaml").write_text(yaml_texto, encoding="utf-8")

    with (ROOT / "configuracao" / "auditoria_selecao_gitstars.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=auditoria[0].keys())
        escritor.writeheader()
        escritor.writerows(auditoria)

    print("Selecao concluida: 50 repositorios.")


if __name__ == "__main__":
    main()
