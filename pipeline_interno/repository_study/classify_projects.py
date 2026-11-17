from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import yaml


COMPLETED = {"passed", "completed_with_errors"}


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def as_number(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


def classify(scan: dict) -> tuple[str, str, float]:
    semgrep_completed = scan.get("semgrep_status") in COMPLETED
    sonar_completed = scan.get("sonar_status") == "passed"
    if not semgrep_completed and not sonar_completed:
        return "pendentes", "nenhuma ferramenta concluiu a análise", 0
    findings = as_number(scan.get("semgrep_total"))
    findings += as_number(scan.get("sonar_vulnerabilities"))
    findings += as_number(scan.get("sonar_security_hotspots"))
    if findings > 0:
        return "com_achados", "ao menos um achado de segurança detectado", findings
    return "sem_achados", "nenhum achado detectado pelas ferramentas concluídas", 0


def ignored(_directory: str, names: list[str]) -> set[str]:
    blocked = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
    return {name for name in names if name in blocked}


def main() -> None:
    cfg = yaml.safe_load(Path("repository_study/config.yaml").read_text(encoding="utf-8"))
    workspace = Path(cfg["workspace"])
    classified_root = workspace / "classificados"
    scans = {(x["repo"], x["origin"]): x for x in read_jsonl(workspace / "security_summary.jsonl")}
    rows = []
    for item in read_jsonl(workspace / "inventory.jsonl"):
        if not item.get("eligible_size"):
            rows.append({"repo": item["repo"], "group": "excluded", "reason": "below_size_threshold", "security_findings": ""})
            continue
        scan = scans.get((item["repo"], "human"), {})
        group, reason, findings = classify(scan)
        slug = item["repo"].replace("/", "__")
        destination = classified_root / group / slug
        if group != "pendentes" and not destination.exists():
            shutil.copytree(item["snapshot_path"], destination, ignore=ignored)
        destination.mkdir(parents=True, exist_ok=True)
        metadata = {
            "repo": item["repo"], "commit_sha": item.get("commit_sha"),
            "group": group, "reason": reason, "security_findings": findings,
            "semgrep_status": scan.get("semgrep_status", "not_run"),
            "sonar_status": scan.get("sonar_status", "not_run"),
            "semgrep_config": scan.get("semgrep_config", cfg["semgrep"]["config"]),
        }
        (destination / "CLASSIFICACAO.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        rows.append({"repo": item["repo"], "group": group, "reason": reason, "security_findings": findings})
    report = classified_root / "classificacao.csv"
    with report.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=["repo", "group", "reason", "security_findings"])
        writer.writeheader()
        writer.writerows(rows)
    print(report.resolve())


if __name__ == "__main__":
    main()
