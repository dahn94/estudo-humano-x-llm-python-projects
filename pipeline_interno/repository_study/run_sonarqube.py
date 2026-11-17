from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

from scan_projects import read_jsonl, targets


METRICS = {
    "bugs": "sonar_bugs",
    "vulnerabilities": "sonar_vulnerabilities",
    "code_smells": "sonar_code_smells",
    "security_hotspots": "sonar_security_hotspots",
    "duplicated_lines_density": "sonar_duplicated_lines_density",
    "ncloc": "sonar_ncloc",
    "complexity": "sonar_complexity",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa SonarScanner e coleta métricas da API do SonarQube.")
    parser.add_argument("--config", default="repository_study/config.yaml")
    parser.add_argument("--origin", choices=("all", "human", "openai", "gemini", "claude"), default="all")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    load_dotenv("secrets/providers.env")
    token = os.getenv(cfg["sonarqube"]["token_env"])
    scanner = shutil.which("sonar-scanner")
    selected = [item for item in targets(cfg) if args.origin == "all" or item["origin"] == args.origin]
    if args.dry_run:
        print(f"Projetos selecionados: {len(selected)}")
        print(f"SonarScanner instalado: {bool(scanner)}")
        print(f"Token configurado: {bool(token)}")
        return
    if not scanner:
        raise SystemExit("sonar-scanner não encontrado no PATH")
    if not token:
        raise SystemExit(f"Configure {cfg['sonarqube']['token_env']} em secrets/providers.env")

    workspace = Path(cfg["workspace"])
    summary_path = workspace / "security_summary.jsonl"
    summaries = read_jsonl(summary_path)
    index = {(x["repo"], x["origin"]): x for x in summaries}
    for item in selected:
        slug = item["repo"].replace("/", "__").lower()
        key = f"prellm-{item['origin']}-{slug}".replace("_", "-")
        target = Path(item["path"]).resolve()
        command = [
            scanner, f"-Dsonar.projectKey={key}", f"-Dsonar.projectName={key}",
            "-Dsonar.sources=.", "-Dsonar.sourceEncoding=UTF-8",
            f"-Dsonar.host.url={cfg['sonarqube']['url']}", f"-Dsonar.token={token}",
        ]
        process = subprocess.run(command, cwd=target, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        record = index.setdefault((item["repo"], item["origin"]), dict(item))
        if process.returncode:
            record.update({"sonar_status": "error", "sonar_error": process.stdout[-4000:]})
            continue
        for _ in range(30):
            response = requests.get(
                f"{cfg['sonarqube']['url']}/api/measures/component",
                params={"component": key, "metricKeys": ",".join(METRICS)},
                auth=(token, ""), timeout=30,
            )
            if response.ok:
                measures = response.json().get("component", {}).get("measures", [])
                record.update({METRICS[x["metric"]]: x.get("value", "") for x in measures if x["metric"] in METRICS})
                record["sonar_status"] = "passed"
                break
            time.sleep(2)
        else:
            record.update({"sonar_status": "error", "sonar_error": "Métricas não ficaram disponíveis"})

    with summary_path.open("w", encoding="utf-8") as stream:
        for record in index.values():
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
