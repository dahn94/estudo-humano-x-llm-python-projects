from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from scan_projects import count_severity, read_jsonl


def main() -> None:
    cfg = yaml.safe_load(Path("repository_study/config.yaml").read_text(encoding="utf-8"))
    workspace = Path(cfg["workspace"])
    inventory = read_jsonl(workspace / "inventory.jsonl")
    summary_path = workspace / "security_summary.jsonl"
    existing = {(x["repo"], x["origin"]): x for x in read_jsonl(summary_path)}

    for item in inventory:
        if not item.get("eligible_size"):
            continue
        slug = item["repo"].replace("/", "__")
        report = workspace / "reports" / "human" / slug / "semgrep.json"
        if not report.exists():
            continue
        payload = json.loads(report.read_text(encoding="utf-8"))
        record = existing.setdefault((item["repo"], "human"), {
            "repo": item["repo"], "purpose": item["purpose"], "origin": "human",
            "model": "human", "path": item["snapshot_path"], "python_loc": item["python_loc"],
        })
        errors = payload.get("errors", [])
        record.update({
            "semgrep_status": "completed_with_errors" if errors else "passed",
            "semgrep_error": json.dumps(errors, ensure_ascii=False)[:4000] if errors else "",
            "semgrep_config": cfg["semgrep"]["config"],
            "semgrep_version": payload.get("version", ""),
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            **count_severity(payload),
        })

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as stream:
        for record in existing.values():
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(summary_path.resolve())


if __name__ == "__main__":
    main()
