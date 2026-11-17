from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / "workspace" / "repository_study"
SLUGS = {
    "anxolerd/dvpwa": "anxolerd__dvpwa",
    "bottlepy/bottle": "bottlepy__bottle",
}


def metric_map(payload: dict) -> dict[str, str]:
    return {item["metric"]: item.get("value", "") for item in payload["component"].get("measures", [])}


def facet_map(payload: dict, name: str) -> dict[str, int]:
    for facet in payload.get("issues_summary", {}).get("facets", []):
        if facet.get("property") == name:
            return {item["val"]: item["count"] for item in facet.get("values", [])}
    return {}


def main() -> None:
    summary_path = WORKSPACE / "security_summary.jsonl"
    rows = [json.loads(line) for line in summary_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        slug = SLUGS.get(row.get("repo"))
        if not slug or row.get("origin") != "human":
            continue
        report = WORKSPACE / "reports" / "human" / slug / "sonar.json"
        if not report.exists():
            continue
        payload = json.loads(report.read_text(encoding="utf-8"))
        metrics = metric_map(payload)
        types = facet_map(payload, "types")
        severities = facet_map(payload, "severities")
        row.update({
            "sonar_status": "passed",
            "sonar_scope": "python_only",
            "sonar_ncloc": int(metrics.get("ncloc", 0) or 0),
            "sonar_complexity": int(metrics.get("complexity", 0) or 0),
            "sonar_bugs": types.get("BUG", 0),
            "sonar_vulnerabilities": types.get("VULNERABILITY", 0),
            "sonar_code_smells": types.get("CODE_SMELL", 0),
            "sonar_security_hotspots": int(metrics.get("security_hotspots", 0) or 0),
            "sonar_security_issues": int(metrics.get("software_quality_security_issues", 0) or 0),
            "sonar_maintainability_issues": int(metrics.get("software_quality_maintainability_issues", 0) or 0),
            "sonar_reliability_issues": int(metrics.get("software_quality_reliability_issues", 0) or 0),
            "sonar_issue_severities": severities,
        })
    summary_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(summary_path.resolve())


if __name__ == "__main__":
    main()
