#!/usr/bin/env bash
set -u

docker start sonarqube-sonarqube-1 >/dev/null 2>&1 || true
for i in $(seq 1 30); do
  status=$(curl -s --max-time 3 http://localhost:9000/api/system/status || true)
  printf 'try=%s %s\n' "$i" "$status"
  if printf '%s' "$status" | grep -q '"status":"UP"'; then
    break
  fi
  sleep 3
done
echo CONTAINER
docker ps -a --format '{{.Names}}|{{.Status}}'
echo LOGS
docker logs --tail 40 sonarqube-sonarqube-1 2>&1
echo SEMGREP
timeout 30 "$HOME/.local/bin/semgrep" --version 2>&1 || echo SEMGREP_TIMEOUT_OR_ERROR
