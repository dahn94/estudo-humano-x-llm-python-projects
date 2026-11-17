from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml


def run(command: list[str], cwd: Path | None = None) -> str:
    env = os.environ.copy()
    if os.name == "nt":
        command = [command[0], "-c", "http.sslBackend=openssl", *command[1:]] if command[0] == "git" else command
    process = subprocess.run(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or process.stdout.strip())
    return process.stdout.strip()


def append_jsonl(path: Path, item: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(item, ensure_ascii=False) + "\n")


def read_limited(paths: list[Path], limit: int) -> str:
    chunks, size = [], 0
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        remaining = limit - size
        if remaining <= 0:
            break
        chunk = text[:remaining]
        chunks.append(f"\n--- {path.name} ---\n{chunk}")
        size += len(chunk)
    return "".join(chunks)


def checkout_snapshot(repo: str, target: Path, cutoff: str) -> tuple[str, str]:
    if not target.exists():
        run(["git", "clone", "--quiet", f"https://github.com/{repo}.git", str(target)])
    else:
        run(["git", "fetch", "--all", "--tags", "--prune"], target)
    sha = run(["git", "rev-list", "-1", f"--before={cutoff} 23:59:59", "--all"], target)
    if not sha:
        raise RuntimeError(f"Nenhum commit anterior a {cutoff}")
    run(["git", "checkout", "--quiet", "--detach", sha], target)
    return sha, run(["git", "show", "-s", "--format=%cI", sha], target)


def project_statistics(root: Path) -> tuple[int, int]:
    files, loc = 0, 0
    for path in root.rglob("*.py"):
        if ".git" in path.parts or any(part in {".venv", "venv", "vendor"} for part in path.parts):
            continue
        files += 1
        loc += len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    return files, loc


def build_prompt(repo: str, readmes: str, docs: str, manifests: str) -> str:
    return f"""Crie do zero um projeto Python funcionalmente semelhante ao projeto descrito abaixo.
Não procure, copie, traduza ou reproduza o código-fonte original. Use somente esta documentação.
Implemente as funcionalidades públicas descritas, testes próprios e instruções de execução.
Retorne exclusivamente JSON válido no formato:
{{"files":[{{"path":"caminho/seguro.ext","content":"conteúdo completo"}}]}}
Não use caminhos absolutos, '..', arquivos binários, segredos ou credenciais.

PROJETO DE REFERÊNCIA: {repo}

README:
{readmes}

DOCUMENTAÇÃO:
{docs}

MANIFESTOS PÚBLICOS:
{manifests}
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="repository_study/config.yaml")
    args = parser.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    workspace = Path(cfg["workspace"])
    repos_root = workspace / "human"
    prompts_path = workspace / "project_prompts.jsonl"
    inventory_path = workspace / "inventory.jsonl"
    prompts_path.parent.mkdir(parents=True, exist_ok=True)
    prompts_path.write_text("", encoding="utf-8")
    inventory_path.write_text("", encoding="utf-8")

    projects = cfg["positive_controls"] + cfg["real_world"]
    for project in projects:
        repo = project["repo"]
        target = repos_root / repo.replace("/", "__")
        print(f"Preparando {repo}...")
        try:
            sha, commit_date = checkout_snapshot(repo, target, cfg["cutoff_date"])
            py_files, py_loc = project_statistics(target)
            readmes = read_limited(sorted(target.glob("README*")), cfg["prompt"]["max_readme_chars"])
            docs = read_limited(sorted(target.glob("docs/**/*.md")), cfg["prompt"]["max_docs_chars"])
            manifests = read_limited(
                [p for name in ("requirements*.txt", "pyproject.toml", "Pipfile") for p in target.glob(name)],
                cfg["prompt"]["max_manifest_chars"],
            )
            eligible = py_files >= cfg["selection"]["minimum_python_files"] and py_loc >= cfg["selection"]["minimum_python_loc"]
            record = {
                "repo": repo, "purpose": project["purpose"], "commit_sha": sha,
                "commit_date": commit_date, "snapshot_path": target.as_posix(),
                "python_files": py_files, "python_loc": py_loc, "eligible_size": eligible,
                "prepared_at": datetime.now(timezone.utc).isoformat(),
            }
            append_jsonl(inventory_path, record)
            if eligible:
                append_jsonl(prompts_path, {
                    "id": repo.replace("/", "__").lower(), "repo": repo, "purpose": project["purpose"],
                    "commit_sha": sha, "prompt": build_prompt(repo, readmes, docs, manifests),
                })
            print(f"  commit={sha[:12]} arquivos_py={py_files} loc_py={py_loc} elegível={eligible}")
        except Exception as exc:
            append_jsonl(inventory_path, {"repo": repo, "purpose": project["purpose"], "status": "error", "error": str(exc)})
            print(f"  ERRO: {exc}")


if __name__ == "__main__":
    main()
