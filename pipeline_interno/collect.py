
from __future__ import annotations

import ast
import csv
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import yaml


@dataclass
class FunctionRecord:
    repo: str
    commit_sha: str
    commit_date: str
    file: str
    qualified_name: str
    signature: str
    start_line: int
    end_line: int
    nloc: int
    docstring: str
    readme_context: str
    test_context: str
    human_code: str
    functional_spec: str
    prompt: str


def run(cmd: list[str], cwd: Path | None = None) -> str:
    p = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        raise RuntimeError(
            f"Comando falhou: {' '.join(cmd)}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
        )
    return p.stdout.strip()


def slug(repo: str) -> str:
    return repo.replace("/", "__")


def clone_or_update(repo: str, root: Path) -> Path:
    target = root / slug(repo)
    url = f"https://github.com/{repo}.git"

    if not target.exists():
        # Clone completo para permitir caminhar no histórico até o corte temporal.
        run(["git", "clone", "--quiet", url, str(target)])
    else:
        run(["git", "fetch", "--all", "--tags", "--prune"], cwd=target)

    return target


def checkout_before(repo_dir: Path, cutoff: str) -> tuple[str, str]:
    """
    Seleciona o commit mais recente alcançável em refs remotas antes do corte.
    cutoff: YYYY-MM-DD
    """
    refs = run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/remotes/origin/"],
        cwd=repo_dir,
    ).splitlines()

    refs = [r for r in refs if not r.endswith("/HEAD")]
    if not refs:
        raise RuntimeError("Nenhuma referência remota encontrada.")

    candidates: list[tuple[int, str, str]] = []
    for ref in refs:
        try:
            sha = run(
                ["git", "rev-list", "-1", f"--before={cutoff} 23:59:59", ref],
                cwd=repo_dir,
            )
            if not sha:
                continue
            ts = int(run(["git", "show", "-s", "--format=%ct", sha], cwd=repo_dir))
            candidates.append((ts, sha, ref))
        except RuntimeError:
            continue

    if not candidates:
        raise RuntimeError(f"Nenhum commit anterior a {cutoff} foi encontrado.")

    candidates.sort(reverse=True)
    _, sha, _ref = candidates[0]

    run(["git", "checkout", "--quiet", "--detach", sha], cwd=repo_dir)
    commit_date = run(
        ["git", "show", "-s", "--format=%cI", sha],
        cwd=repo_dir,
    )
    return sha, commit_date


def iter_python_files(repo_dir: Path, excluded_dirs: set[str]) -> Iterable[Path]:
    for path in repo_dir.rglob("*.py"):
        rel = path.relative_to(repo_dir)
        if any(part in excluded_dirs for part in rel.parts):
            continue
        if ".git" in rel.parts:
            continue
        yield path


def get_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = []

    posonly = getattr(node.args, "posonlyargs", [])
    positional = posonly + node.args.args
    defaults = [None] * (len(positional) - len(node.args.defaults)) + list(node.args.defaults)

    for arg, default in zip(positional, defaults):
        s = arg.arg
        if default is not None:
            try:
                s += "=" + ast.unparse(default)
            except Exception:
                s += "=..."
        args.append(s)

    if node.args.vararg:
        args.append("*" + node.args.vararg.arg)
    elif node.args.kwonlyargs:
        args.append("*")

    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        s = arg.arg
        if default is not None:
            try:
                s += "=" + ast.unparse(default)
            except Exception:
                s += "=..."
        args.append(s)

    if node.args.kwarg:
        args.append("**" + node.args.kwarg.arg)

    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({', '.join(args)})"


def collect_functions(source: str):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
    records = []

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def _visit_func(self, node):
            qname = ".".join(self.stack + [node.name])
            start = node.lineno
            end = getattr(node, "end_lineno", node.lineno)
            code = "\n".join(lines[start - 1:end])
            doc = ast.get_docstring(node, clean=True) or ""
            records.append(
                {
                    "qualified_name": qname,
                    "signature": get_signature(node),
                    "start_line": start,
                    "end_line": end,
                    "nloc": max(1, end - start + 1),
                    "docstring": doc,
                    "human_code": code,
                }
            )
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self._visit_func(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self._visit_func(node)

    Visitor().visit(tree)
    return records


def context_around_matches(path: Path, term: str, radius: int = 5, max_hits: int = 3) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

    lines = text.splitlines()
    out = []
    pattern = re.compile(rf"\b{re.escape(term)}\b", re.I)

    for i, line in enumerate(lines):
        if pattern.search(line):
            lo = max(0, i - radius)
            hi = min(len(lines), i + radius + 1)
            chunk = "\n".join(lines[lo:hi])
            out.append(f"[{path.name}:{lo+1}-{hi}]\n{chunk}")
            if len(out) >= max_hits:
                break
    return "\n\n".join(out)


def find_readme_context(repo_dir: Path, term: str) -> str:
    candidates = []
    for pattern in ("README*", "docs/**/*.md", "doc/**/*.md"):
        candidates.extend(repo_dir.glob(pattern))

    chunks = []
    for p in candidates[:100]:
        if p.is_file():
            c = context_around_matches(p, term, radius=4, max_hits=2)
            if c:
                chunks.append(c)
                if len(chunks) >= 3:
                    break
    return "\n\n".join(chunks)


def find_test_context(repo_dir: Path, term: str) -> str:
    chunks = []
    candidates = list(repo_dir.rglob("test*.py")) + list(repo_dir.rglob("*_test.py"))
    seen = set()
    for p in candidates:
        if p in seen:
            continue
        seen.add(p)
        c = context_around_matches(p, term, radius=6, max_hits=2)
        if c:
            chunks.append(c)
            if len(chunks) >= 3:
                break
    return "\n\n".join(chunks)


def clean_docstring(doc: str, max_chars: int = 1200) -> str:
    doc = re.sub(r"\s+", " ", doc).strip()
    return doc[:max_chars]


def build_functional_spec(signature: str, docstring: str) -> str:
    """
    Especificação determinística e neutra.
    Não usa o corpo do código humano.
    """
    doc = clean_docstring(docstring)
    if not doc:
        return ""

    return (
        f"Linguagem: Python\n"
        f"Assinatura de referência: {signature}\n"
        f"Objetivo funcional: {doc}"
    )


def build_prompt(functional_spec: str) -> str:
    return (
        "Implemente em Python a funcionalidade descrita abaixo do zero.\n"
        "Não utilize bibliotecas externas, a menos que sejam indispensáveis ao requisito.\n"
        "Retorne somente o código Python, sem explicações adicionais.\n"
        "Preserve a interface solicitada quando houver uma assinatura indicada.\n\n"
        f"{functional_spec}"
    )


def is_candidate(fn: dict, cfg: dict) -> bool:
    name = fn["qualified_name"].split(".")[-1]

    if name.startswith("__") and name.endswith("__"):
        return False

    if fn["nloc"] < cfg["min_function_lines"]:
        return False

    if fn["nloc"] > cfg["max_function_lines"]:
        return False

    doc = clean_docstring(fn["docstring"])
    if cfg.get("require_docstring", True) and len(doc) < cfg["min_docstring_chars"]:
        return False

    blocked = set(cfg.get("blocked_function_names", []))
    if name in blocked:
        return False

    return True


def write_csv(records: list[FunctionRecord], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(records[0]).keys()) if records else [
        "repo","commit_sha","commit_date","file","qualified_name","signature",
        "start_line","end_line","nloc","docstring","readme_context","test_context",
        "human_code","functional_spec","prompt"
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow(asdict(r))


def write_jsonl(records: list[FunctionRecord], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


def main():
    cfg = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))

    root = Path(cfg["workspace"])
    repos_root = root / "repos"
    output_root = root / "output"
    repos_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    all_records: list[FunctionRecord] = []

    for repo in cfg["repositories"]:
        print(f"\n=== {repo} ===")
        try:
            repo_dir = clone_or_update(repo, repos_root)
            sha, commit_date = checkout_before(repo_dir, cfg["cutoff_date"])
            print(f"Commit selecionado: {sha[:12]} | {commit_date}")
        except Exception as e:
            print(f"[ERRO] {repo}: {e}")
            continue

        repo_records = []
        for pyfile in iter_python_files(repo_dir, set(cfg["excluded_dirs"])):
            rel = pyfile.relative_to(repo_dir).as_posix()
            try:
                source = pyfile.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for fn in collect_functions(source):
                if not is_candidate(fn, cfg):
                    continue

                short_name = fn["qualified_name"].split(".")[-1]
                readme_context = find_readme_context(repo_dir, short_name)
                test_context = find_test_context(repo_dir, short_name)

                spec = build_functional_spec(fn["signature"], fn["docstring"])
                if not spec:
                    continue

                record = FunctionRecord(
                    repo=repo,
                    commit_sha=sha,
                    commit_date=commit_date,
                    file=rel,
                    qualified_name=fn["qualified_name"],
                    signature=fn["signature"],
                    start_line=fn["start_line"],
                    end_line=fn["end_line"],
                    nloc=fn["nloc"],
                    docstring=clean_docstring(fn["docstring"]),
                    readme_context=readme_context,
                    test_context=test_context,
                    human_code=fn["human_code"],
                    functional_spec=spec,
                    prompt=build_prompt(spec),
                )
                repo_records.append(record)

        limit = cfg.get("max_functions_per_repo")
        if limit:
            repo_records = repo_records[: int(limit)]

        print(f"Funções candidatas: {len(repo_records)}")
        all_records.extend(repo_records)

    write_csv(all_records, output_root / "dataset_humano.csv")
    write_jsonl(all_records, output_root / "dataset_humano.jsonl")

    prompts_path = output_root / "prompts.jsonl"
    with prompts_path.open("w", encoding="utf-8") as f:
        for i, r in enumerate(all_records, start=1):
            f.write(json.dumps({
                "id": f"sample_{i:05d}",
                "repo": r.repo,
                "commit_sha": r.commit_sha,
                "file": r.file,
                "qualified_name": r.qualified_name,
                "prompt": r.prompt
            }, ensure_ascii=False) + "\n")

    print(f"\nConcluído. Total: {len(all_records)} funções.")
    print(f"Saída: {output_root.resolve()}")


if __name__ == "__main__":
    main()
