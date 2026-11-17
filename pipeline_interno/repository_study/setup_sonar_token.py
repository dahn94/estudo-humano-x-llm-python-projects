from __future__ import annotations

import os
from pathlib import Path

import requests


def main() -> None:
    target = Path("secrets/sonar.env")
    if target.exists() and any(line.startswith("SONAR_TOKEN=") and line.strip() != "SONAR_TOKEN=" for line in target.read_text(encoding="utf-8").splitlines()):
        print(f"Token SonarQube já configurado em {target}")
        return
    response = requests.post(
        "http://localhost:9000/api/user_tokens/generate",
        data={"name": "python-repository-study"},
        auth=("admin", "admin"), timeout=30,
    )
    response.raise_for_status()
    token = response.json()["token"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"SONAR_TOKEN={token}\n", encoding="utf-8")
    print(f"Token SonarQube salvo com segurança em {target}")


if __name__ == "__main__":
    main()

