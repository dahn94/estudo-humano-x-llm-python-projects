"""SonarQube local em Docker: subir, autenticar e consultar resultados.

Uso:
    uv run scripts/sonarqube.py preparar   # sobe o contêiner e grava o token em .sonar/token
    uv run scripts/sonarqube.py parar
"""
from __future__ import annotations

import base64
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from comum import ROOT

URL = os.environ.get("SONAR_URL", "http://localhost:9000")
PASTA = ROOT / ".sonar"
METRICAS = "ncloc,complexity,security_hotspots,bugs,vulnerabilities,code_smells,software_quality_security_issues,software_quality_maintainability_issues,software_quality_reliability_issues"
LIMITE_BUSCA = 10_000  # api/issues/search não pagina além disso


def _requisicao(caminho: str, auth: str, dados: dict | None = None) -> dict:
    corpo = urllib.parse.urlencode(dados).encode() if dados is not None else None
    req = urllib.request.Request(URL + caminho, data=corpo, method="POST" if corpo is not None else "GET")
    req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    with urllib.request.urlopen(req, timeout=60) as resp:
        texto = resp.read()
    return json.loads(texto) if texto else {}


def get(caminho: str, token: str) -> dict:
    return _requisicao(caminho, f"{token}:")


def aguardar(limite_s: int = 300) -> None:
    fim = time.time() + limite_s
    while time.time() < fim:
        try:
            with urllib.request.urlopen(URL + "/api/system/status", timeout=3) as resp:
                if json.load(resp).get("status") == "UP":
                    return
        except (urllib.error.URLError, OSError, ValueError):
            pass
        time.sleep(3)
    raise SystemExit(f"SonarQube não respondeu em {URL}. Veja: docker compose logs sonarqube")


def token() -> str:
    if valor := os.environ.get("SONAR_TOKEN", "").strip():
        return valor
    arquivo = PASTA / "token"
    if arquivo.exists():
        return arquivo.read_text().strip()
    raise SystemExit("Sem token do SonarQube. Rode: uv run scripts/sonarqube.py preparar")


def preparar() -> None:
    subprocess.run(["docker", "compose", "up", "-d", "sonarqube"], cwd=ROOT, check=True)
    aguardar()
    PASTA.mkdir(exist_ok=True)
    if (PASTA / "token").exists():
        print("Token já existe em .sonar/token")
        return
    senha_arquivo = PASTA / "admin_password"
    if senha_arquivo.exists():
        senha = senha_arquivo.read_text().strip()
    else:
        # Primeiro uso: a imagem vem com admin/admin e exige troca de senha.
        senha = secrets.token_urlsafe(18) + "Aa1!"
        _requisicao("/api/users/change_password", "admin:admin", {"login": "admin", "previousPassword": "admin", "password": senha})
        senha_arquivo.write_text(senha)
        senha_arquivo.chmod(0o600)
    gerado = _requisicao("/api/user_tokens/generate", f"admin:{senha}", {"name": f"estudo-{int(time.time())}"})
    (PASTA / "token").write_text(gerado["token"])
    (PASTA / "token").chmod(0o600)
    print("Token gravado em .sonar/token (fora do git)")


def aguardar_tarefa(ce_task_id: str, tok: str, limite_s: int = 3600) -> None:
    """Espera o processamento do relatório no servidor; antes disso as issues vêm vazias."""
    fim = time.time() + limite_s
    while time.time() < fim:
        status = get(f"/api/ce/task?id={ce_task_id}", tok)["task"]["status"]
        if status == "SUCCESS":
            return
        if status in {"FAILED", "CANCELED"}:
            raise RuntimeError(f"Tarefa {ce_task_id} terminou com {status}")
        time.sleep(3)
    raise RuntimeError(f"Tarefa {ce_task_id} não terminou em {limite_s}s")


def coletar(chave: str, tok: str) -> dict:
    """Medidas do projeto + todas as issues, no formato de dados_brutos/sonarqube."""
    q = urllib.parse.urlencode({"component": chave, "metricKeys": METRICAS})
    payload = get(f"/api/measures/component?{q}", tok)
    issues: list[dict] = []
    pagina = 1
    while True:
        q = urllib.parse.urlencode({"componentKeys": chave, "p": pagina, "ps": 500})
        resposta = get(f"/api/issues/search?{q}", tok)
        total = int(resposta.get("paging", {}).get("total", 0))
        if total > LIMITE_BUSCA:
            raise RuntimeError(f"{chave}: {total} issues excedem o limite de {LIMITE_BUSCA} da API de busca")
        issues.extend(resposta.get("issues", []))
        if len(issues) >= total or not resposta.get("issues"):
            break
        pagina += 1

    medidas = {m["metric"]: int(float(m.get("value", 0))) for m in payload.get("component", {}).get("measures", [])}
    esperado = sum(medidas.get(k, 0) for k in ("bugs", "vulnerabilities", "code_smells"))
    if len(issues) != esperado:
        raise RuntimeError(f"{chave}: {len(issues)} issues baixadas, mas as medidas somam {esperado}")
    payload["issues_summary"] = {"issues": issues, "paging": {"total": len(issues)}}
    return payload


def main() -> None:
    comando = sys.argv[1] if len(sys.argv) > 1 else ""
    if comando == "preparar":
        preparar()
    elif comando == "parar":
        subprocess.run(["docker", "compose", "stop", "sonarqube"], cwd=ROOT, check=True)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
