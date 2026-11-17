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
    scans = {(x["repo"], x["origin"]): x for x in read_jsonl(workspace / "security_summary.jsonl")}
    rows = []
    for item in read_jsonl(workspace / "inventory.jsonl"):
        scan = scans.get((item["repo"], "human"), {})
        size_ok = bool(item.get("eligible_size"))
        findings = scan.get("semgrep_total")
        if not size_ok:
            decision, reason = "excluded", "below_size_threshold"
        elif scan.get("semgrep_status") not in {"passed", "completed_with_errors"}:
            decision, reason = "pending", "semgrep_not_completed"
        elif findings < cfg["selection"]["minimum_semgrep_findings"]:
            decision, reason = "excluded", "no_semgrep_findings"
        else:
            decision, reason = "included", "criteria_met"
        rows.append({
            "repo": item["repo"], "purpose": item["purpose"],
            "commit_sha": item.get("commit_sha", ""), "python_files": item.get("python_files", ""),
            "python_loc": item.get("python_loc", ""), "semgrep_status": scan.get("semgrep_status", "not_run"),
            "semgrep_findings": findings if findings is not None else "", "decision": decision, "reason": reason,
        })
    output = workspace / "selection_report.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["repo"])
        writer.writeheader()
        writer.writerows(rows)
    print(output.resolve())


if __name__ == "__main__":
    main()
