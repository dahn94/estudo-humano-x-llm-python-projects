from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    cfg = yaml.safe_load(Path("repository_study/config.yaml").read_text(encoding="utf-8"))
    workspace = Path(cfg["workspace"])
    scans = read_jsonl(workspace / "security_summary.jsonl")
    fields = [
        "repo", "purpose", "origin", "model", "python_loc", "semgrep_config",
        "semgrep_status", "semgrep_total", "semgrep_error", "semgrep_warning",
        "semgrep_info", "semgrep_unknown", "semgrep_cwes", "sonar_status",
        "sonar_bugs", "sonar_vulnerabilities", "sonar_code_smells",
        "sonar_security_hotspots", "sonar_duplicated_lines_density", "test_status",
    ]
    output = workspace / "resultado_comparativo_projetos.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for item in scans:
            row = {field: item.get(field, "") for field in fields}
            row["semgrep_cwes"] = "; ".join(item.get("semgrep_cwes", []))
            row["sonar_status"] = item.get("sonar_status", "not_run")
            row["test_status"] = item.get("test_status", "not_run")
            writer.writerow(row)
    print(output.resolve())


if __name__ == "__main__":
    main()

