from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SONAR_URL = "http://localhost:9000"
PROJECTS = (
    ("human-anxolerd-dvpwa", "anxolerd__dvpwa"),
    ("human-bottlepy-bottle", "bottlepy__bottle"),
)
METRICS = (
    "ncloc,complexity,security_hotspots,software_quality_security_issues,"
    "software_quality_maintainability_issues,software_quality_reliability_issues"
)


def get_json(path: str, token: str) -> dict:
    request = urllib.request.Request(SONAR_URL + path)
    auth = base64.b64encode(f"{token}:".encode()).decode()
    request.add_header("Authorization", f"Basic {auth}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> None:
    token = (ROOT / "secrets" / "sonar.env").read_text(encoding="utf-8").strip().split("=", 1)[1]
    for project_key, slug in PROJECTS:
        query = urllib.parse.urlencode({"component": project_key, "metricKeys": METRICS})
        payload = get_json(f"/api/measures/component?{query}", token)
        issues_query = urllib.parse.urlencode({"componentKeys": project_key, "ps": 500, "facets": "severities,types"})
        payload["issues_summary"] = get_json(f"/api/issues/search?{issues_query}", token)
        report = ROOT / "workspace" / "repository_study" / "reports" / "human" / slug / "sonar.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Métricas atualizadas: {report}")


if __name__ == "__main__":
    main()
