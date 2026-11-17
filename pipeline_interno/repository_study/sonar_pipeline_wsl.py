from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SONAR_URL = "http://localhost:9000"
PROJECTS = (
    ("human-anxolerd-dvpwa", "anxolerd__dvpwa"),
    ("human-bottlepy-bottle", "bottlepy__bottle"),
)
METRICS = "bugs,vulnerabilities,code_smells,security_hotspots,duplicated_lines_density,ncloc,complexity"


def request(path: str, *, data: dict | None = None, user: str = "", password: str = "") -> dict:
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(SONAR_URL + path, data=body)
    if user:
        auth = base64.b64encode(f"{user}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {auth}")
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def wait_until_ready() -> None:
    for _ in range(60):
        try:
            if request("/api/system/status").get("status") == "UP":
                return
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError("SonarQube não ficou pronto")


def wait_for_measures(project_key: str, token: str) -> dict:
    query = urllib.parse.urlencode({"component": project_key, "metricKeys": METRICS})
    for _ in range(60):
        try:
            return request(f"/api/measures/component?{query}", user=token, password="")
        except HTTPError as exc:
            if exc.code != 404:
                raise
        time.sleep(2)
    raise RuntimeError(f"Métricas de {project_key} não ficaram disponíveis")


def main() -> None:
    subprocess.run(["docker", "start", "sonarqube-sonarqube-1"], check=False)
    wait_until_ready()
    secret_path = ROOT / "secrets" / "sonar.env"
    if secret_path.exists() and secret_path.read_text(encoding="utf-8").startswith("SONAR_TOKEN="):
        token = secret_path.read_text(encoding="utf-8").strip().split("=", 1)[1]
        print("Reutilizando token SonarQube local.", flush=True)
    else:
        token_data = request(
            "/api/user_tokens/generate",
            data={"name": f"repository-study-{int(time.time())}"},
            user="admin", password="admin",
        )
        token = token_data["token"]
        secret_path.write_text(f"SONAR_TOKEN={token}\n", encoding="utf-8")
        print("Token SonarQube salvo sem exibir o valor.", flush=True)

    for key, slug in PROJECTS:
        source = ROOT / "workspace" / "repository_study" / "human" / slug
        print(f"Analisando {slug} no SonarQube...", flush=True)
        scanner = ROOT / "tools" / "sonar-scanner" / "bin" / "sonar-scanner"
        environment = os.environ.copy()
        environment.update({"SONAR_HOST_URL": SONAR_URL, "SONAR_TOKEN": token})
        subprocess.run([
            str(scanner),
            f"-Dsonar.projectKey={key}", f"-Dsonar.projectName={key}",
            "-Dsonar.scanner.skipJreProvisioning=true",
            "-Dsonar.sources=.", "-Dsonar.inclusions=**/*.py",
            "-Dsonar.sourceEncoding=UTF-8", "-Dsonar.python.version=3",
        ], cwd=source, env=environment, check=True)
        payload = wait_for_measures(key, token)
        report = ROOT / "workspace" / "repository_study" / "reports" / "human" / slug / "sonar.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Relatório salvo: {report}")


if __name__ == "__main__":
    main()
