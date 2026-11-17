from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def syntax_check(path: Path) -> tuple[str, str]:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return "passed", ""
    except (SyntaxError, UnicodeError) as exc:
        return "failed", f"{type(exc).__name__}: {exc}"


def semgrep_check(path: Path) -> tuple[str, int | None, str]:
    scripts = Path(sys.executable).parent
    bundled = scripts / "pysemgrep.exe"
    executable = str(bundled) if bundled.exists() else shutil.which("semgrep")
    if not executable:
        return "not_installed", None, "Semgrep não encontrado no PATH"
    analysis_root = Path("workspace/analysis").resolve()
    analysis_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
        "SEMGREP_SEND_METRICS": "off",
        "SEMGREP_LOG_FILE": str(analysis_root / "semgrep.log"),
        "SEMGREP_VERSION_CACHE_PATH": str(analysis_root / "semgrep_version"),
    })
    proc = subprocess.run(
        [executable, "scan", "--config", "semgrep-rules.yaml", "--json", "--quiet", str(path)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
    )
    try:
        payload = json.loads(proc.stdout or "{}")
        findings = len(payload.get("results", []))
    except json.JSONDecodeError:
        return "error", None, proc.stderr.strip() or "JSON inválido do Semgrep"
    return ("passed" if proc.returncode in (0, 1) else "error"), findings, proc.stderr.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida sintaxe e executa Semgrep nos códigos gerados.")
    parser.add_argument("--config", default="generation.yaml")
    args = parser.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    root = Path(cfg["generated_root"])
    output = Path("workspace/analysis/analysis.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("", encoding="utf-8")

    files = sorted(root.glob("*/*.py"))
    for path in files:
        provider = path.parent.name
        syntax_status, syntax_error = syntax_check(path)
        semgrep_status, findings, semgrep_error = semgrep_check(path)
        append_jsonl(output, {
            "sample_id": path.stem,
            "provider": provider,
            "syntax_status": syntax_status,
            "syntax_error": syntax_error,
            "test_status": "not_configured",
            "test_detail": "É necessário definir uma suíte reproduzível/injeção por repositório.",
            "semgrep_status": semgrep_status,
            "semgrep_findings": findings,
            "semgrep_error": semgrep_error,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        })
        print(f"{provider}/{path.name}: sintaxe={syntax_status}, semgrep={semgrep_status}, achados={findings}")
    print(f"Analisados: {len(files)} arquivo(s)")


if __name__ == "__main__":
    main()
