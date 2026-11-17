#!/usr/bin/env bash
set -euo pipefail

slug="$1"
project_key="$2"
root="$(cd "$(dirname "$0")/.." && pwd)"
source_dir="$root/projetos/$slug/humano"
semgrep_output="$root/dados_brutos/semgrep/$slug/humano.json"
sonar_output="$root/dados_brutos/sonarqube/$slug/humano.json"
technical_logs="$root/resultados/resultados_scan_humano/$slug/logs_tecnicos"

mkdir -p "$(dirname "$semgrep_output")" "$(dirname "$sonar_output")" "$technical_logs"
scan_dir="$(mktemp -d -p "$HOME" "prellm_${slug//[^A-Za-z0-9]/_}_XXXX")"
trap 'rm -rf -- "$scan_dir"' EXIT
cd "$source_dir"
find . -type f -name '*.py' \
  -not -path './.git/*' -not -path '*/.venv/*' -not -path '*/venv/*' \
  -not -path '*/vendor/*' -not -path '*/vendors/*' -not -path '*/third_party/*' \
  -not -path '*/node_modules/*' -not -path '*/build/*' -not -path '*/dist/*' \
  -print0 | tar --null -T - -cf - | tar -xf - -C "$scan_dir"
cd "$scan_dir"
export SEMGREP_ENABLE_VERSION_CHECK=0
export SEMGREP_SEND_METRICS=off
export SEMGREP_LOG_FILE="$technical_logs/semgrep.log"

if [[ ! -s "$semgrep_output" ]]; then
  "$HOME/.local/bin/semgrep" scan \
    --config "$root/pipeline_interno/semgrep-rules.yaml" \
    --json --metrics off --timeout 30 --timeout-threshold 5 \
    . >"$semgrep_output" 2>"$technical_logs/semgrep.stderr.log" || semgrep_rc=$?
  semgrep_rc="${semgrep_rc:-0}"
  printf '%s\n' "$semgrep_rc" >"$technical_logs/semgrep_exit_code.txt"
fi

docker start sonarqube-sonarqube-1 >/dev/null 2>&1 || true
for _ in $(seq 1 90); do
  status="$(curl -s --max-time 3 http://localhost:9000/api/system/status || true)"
  if printf '%s' "$status" | grep -q '"status":"UP"'; then break; fi
  sleep 2
done
printf '%s' "$status" | grep -q '"status":"UP"' || { echo 'SonarQube indisponivel' >&2; exit 20; }

set -a
source "$root/pipeline_interno/secrets/sonar.env"
set +a
scanner="$root/pipeline_interno/tools/sonar-scanner/bin/sonar-scanner"
export SONAR_SCANNER_JAVA_OPTS="-Xms256m -Xmx2048m"
"$scanner" \
  -Dsonar.projectKey="$project_key" \
  -Dsonar.projectName="Humano - $slug" \
  -Dsonar.host.url=http://localhost:9000 \
  -Dsonar.token="$SONAR_TOKEN" \
  -Dsonar.scanner.skipJreProvisioning=true \
  -Dsonar.sources=. \
  -Dsonar.inclusions='**/*.py' \
  -Dsonar.exclusions='**/.git/**,**/.venv/**,**/venv/**,**/vendor/**,**/vendors/**,**/third_party/**,**/node_modules/**,**/build/**,**/dist/**' \
  -Dsonar.sourceEncoding=UTF-8 \
  -Dsonar.python.version=3 \
  >"$technical_logs/sonarqube_scanner.log" 2>&1

python3 "$root/pipeline_interno/fetch_one_sonar.py" "$project_key" "$sonar_output" "$root/pipeline_interno/secrets/sonar.env"
