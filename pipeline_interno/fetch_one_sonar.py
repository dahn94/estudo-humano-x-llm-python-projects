from __future__ import annotations

import base64
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

URL = "http://localhost:9000"
METRICS = "ncloc,complexity,security_hotspots,bugs,vulnerabilities,code_smells,software_quality_security_issues,software_quality_maintainability_issues,software_quality_reliability_issues"


def get(path: str, token: str) -> dict:
    request = urllib.request.Request(URL + path)
    request.add_header("Authorization", "Basic " + base64.b64encode(f"{token}:".encode()).decode())
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main() -> None:
    key, output, secret = sys.argv[1:4]
    token = Path(secret).read_text(encoding="utf-8").strip().split("=", 1)[1]
    query = urllib.parse.urlencode({"component": key, "metricKeys": METRICS})
    measures = None
    for _ in range(180):
        try:
            candidate = get(f"/api/measures/component?{query}", token)
            if candidate.get("component", {}).get("measures"):
                measures = candidate
                break
        except Exception:
            pass
        time.sleep(2)
    if measures is None:
        raise RuntimeError("Metricas SonarQube nao ficaram disponiveis")
    issues: list[dict] = []
    page = 1
    while True:
        params = urllib.parse.urlencode({"componentKeys": key, "p": page, "ps": 500})
        payload = get(f"/api/issues/search?{params}", token)
        issues.extend(payload.get("issues", []))
        total = int(payload.get("paging", {}).get("total", len(issues)))
        if len(issues) >= total:
            break
        page += 1
    measures["issues_summary"] = {"issues": issues, "paging": {"total": len(issues)}}
    Path(output).write_text(json.dumps(measures, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
