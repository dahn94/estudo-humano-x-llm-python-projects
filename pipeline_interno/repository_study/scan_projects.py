from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def semgrep_executable() -> str | None:
    scripts = Path(sys.executable).parent
    for name in ("pysemgrep.exe", "semgrep.exe", "pysemgrep", "semgrep"):
        candidate = scripts / name
        if candidate.exists():
            return str(candidate)
    return shutil.which("semgrep")


def count_severity(payload: dict) -> dict:
    counts = {"ERROR": 0, "WARNING": 0, "INFO": 0, "UNKNOWN": 0}
    cwes: set[str] = set()
    for result in payload.get("results", []):
        severity = result.get("extra", {}).get("severity", "UNKNOWN").upper()
        counts[severity if severity in counts else "UNKNOWN"] += 1
        metadata = result.get("extra", {}).get("metadata", {})
        raw_cwe = metadata.get("cwe", [])
        if isinstance(raw_cwe, str):
            raw_cwe = [raw_cwe]
        cwes.update(str(value) for value in raw_cwe)
    return {"semgrep_total": sum(counts.values()), **{f"semgrep_{k.lower()}": v for k, v in counts.items()}, "semgrep_cwes": sorted(cwes)}


def run_semgrep(target: Path, raw_output: Path, config: str, metrics: str) -> dict:
    executable = semgrep_executable()
    if not executable:
        return {"semgrep_status": "not_installed", "semgrep_error": "Executável não encontrado"}
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update({
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
        "SEMGREP_SEND_METRICS": metrics,
        "SEMGREP_LOG_FILE": str(raw_output.with_suffix(".log")),
        "SEMGREP_VERSION_CACHE_PATH": str(raw_output.with_name("semgrep_version")),
    })
    command = [executable, "scan", "--config", config, "--json", "--metrics", metrics, str(target)]
    try:
        process = subprocess.run(
            command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=environment, timeout=600,
        )
    except subprocess.TimeoutExpired:
        return {"semgrep_status": "timeout", "semgrep_error": "Semgrep excedeu 600 segundos"}
    try:
        payload = json.loads(process.stdout)
        raw_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except json.JSONDecodeError:
        return {"semgrep_status": "error", "semgrep_error": (process.stderr or process.stdout).strip()[-4000:]}
    errors = payload.get("errors", [])
    return {
        "semgrep_status": "passed" if not errors else "completed_with_errors",
        "semgrep_error": json.dumps(errors, ensure_ascii=False)[:4000] if errors else "",
        **count_severity(payload),
    }


def targets(cfg: dict) -> list[dict]:
    workspace = Path(cfg["workspace"])
    found = []
    for item in read_jsonl(workspace / "inventory.jsonl"):
        if item.get("eligible_size"):
            found.append({"repo": item["repo"], "origin": "human", "model": "human", "path": item["snapshot_path"], "purpose": item["purpose"], "python_loc": item["python_loc"]})
    generated = workspace / "generated"
    if generated.exists():
        for provider_dir in generated.iterdir():
            if not provider_dir.is_dir():
                continue
            for project_dir in provider_dir.iterdir():
                if project_dir.is_dir():
                    found.append({"repo": project_dir.name.replace("__", "/"), "origin": provider_dir.name, "model": provider_dir.name, "path": project_dir.as_posix(), "purpose": "generated", "python_loc": None})
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa a mesma política Semgrep em humanos e IAs.")
    parser.add_argument("--config", default="repository_study/config.yaml")
    parser.add_argument("--origin", choices=("all", "human", "openai", "gemini", "claude"), default="all")
    parser.add_argument("--local-rules", action="store_true", help="Usa regras locais quando o Registry não estiver acessível.")
    args = parser.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    workspace = Path(cfg["workspace"])
    summary_path = workspace / "security_summary.jsonl"
    existing = read_jsonl(summary_path)
    retained = [x for x in existing if args.origin != "all" and x.get("origin") != args.origin]
    configuration = "semgrep-rules.yaml" if args.local_rules else cfg["semgrep"]["config"]

    results = []
    for item in targets(cfg):
        if args.origin != "all" and item["origin"] != args.origin:
            continue
        slug = item["repo"].replace("/", "__")
        raw = workspace / "reports" / item["origin"] / slug / "semgrep.json"
        print(f"Semgrep: {item['origin']} / {item['repo']}")
        scan = run_semgrep(Path(item["path"]), raw, configuration, cfg["semgrep"]["metrics"])
        record = {**item, **scan, "semgrep_config": configuration, "scanned_at": datetime.now(timezone.utc).isoformat()}
        results.append(record)
        print(f"  status={scan['semgrep_status']} achados={scan.get('semgrep_total')}")
    with summary_path.open("w", encoding="utf-8") as stream:
        for item in retained + results:
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
