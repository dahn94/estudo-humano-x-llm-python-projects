#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"
set -a
source secrets/sonar.env
set +a

scan_project() {
  local project_key="$1"
  local project_name="$2"
  local source_path="$3"
  docker run --rm --network host \
    -e SONAR_HOST_URL="http://localhost:9000" \
    -e SONAR_TOKEN="$SONAR_TOKEN" \
    -v "$project_root/$source_path:/usr/src" \
    sonarsource/sonar-scanner-cli \
    -Dsonar.projectKey="$project_key" \
    -Dsonar.projectName="$project_name" \
    -Dsonar.sources=. \
    -Dsonar.sourceEncoding=UTF-8 \
    -Dsonar.python.version=3
}

scan_project "human-anxolerd-dvpwa" "Humano - anxolerd/dvpwa" "workspace/repository_study/human/anxolerd__dvpwa"
scan_project "human-bottlepy-bottle" "Humano - bottlepy/bottle" "workspace/repository_study/human/bottlepy__bottle"

echo "SONAR_SCANS_COMPLETED"
