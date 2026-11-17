from __future__ import annotations

import csv
import json
import shutil
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "workspace" / "repository_study"
PACKAGE = ROOT / "estudo_comparativo"
ORIGINS = ("humano", "openai", "gemini", "claude")


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def ignore(_directory: str, names: list[str]) -> set[str]:
    blocked = {".git", ".scannerwork", "__pycache__", ".pytest_cache", ".venv", "venv"}
    return {name for name in names if name in blocked or name.endswith(".pyc")}


def python_loc(path: Path) -> int | str:
    if not path.exists():
        return ""
    files = [
        file for file in path.rglob("*.py")
        if not any(part in {".git", ".venv", "venv", "__pycache__"} for part in file.parts)
    ]
    if not files:
        return ""
    total = 0
    for file in files:
        try:
            total += sum(1 for line in file.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip())
        except OSError:
            pass
    return total


def semgrep_metrics(path: Path) -> dict:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    severities = Counter(x.get("extra", {}).get("severity", "UNKNOWN") for x in payload.get("results", []))
    cwes = Counter()
    for result in payload.get("results", []):
        values = result.get("extra", {}).get("metadata", {}).get("cwe", [])
        if isinstance(values, str):
            values = [values]
        cwes.update(values)
    return {
        "semgrep_status": "concluido" if not payload.get("errors") else "concluido_com_erros",
        "semgrep_total": len(payload.get("results", [])),
        "semgrep_error": severities.get("ERROR", 0),
        "semgrep_warning": severities.get("WARNING", 0),
        "semgrep_info": severities.get("INFO", 0),
        "semgrep_erros_operacionais": len(payload.get("errors", [])),
        "semgrep_cwes": "; ".join(f"{key} ({value})" for key, value in sorted(cwes.items())),
    }


def sonar_metrics(path: Path) -> dict:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    issues = payload.get("issues_summary", {}).get("issues", [])
    types = Counter(x.get("type", "UNKNOWN") for x in issues)
    severities = Counter(x.get("severity", "UNKNOWN") for x in issues)
    measures = {x["metric"]: x.get("value", "") for x in payload.get("component", {}).get("measures", [])}
    return {
        "sonarqube_status": "concluido",
        "sonarqube_total": len(issues),
        "sonarqube_vulnerabilidades": types.get("VULNERABILITY", 0),
        "sonarqube_bugs": types.get("BUG", 0),
        "sonarqube_code_smells": types.get("CODE_SMELL", 0),
        "sonarqube_hotspots": int(measures.get("security_hotspots", 0) or 0),
        "sonarqube_severidades": "; ".join(f"{key}={value}" for key, value in sorted(severities.items())),
        "sonarqube_complexidade": measures.get("complexity", ""),
        "sonarqube_ncloc": measures.get("ncloc", ""),
    }


def main() -> None:
    inventory = {x["repo"]: x for x in jsonl(SOURCE / "inventory.jsonl") if x.get("eligible_size")}
    prompts = {x["repo"]: x for x in jsonl(SOURCE / "project_prompts.jsonl")}
    for folder in ("configuracao", "prompts", "projetos", "dados_brutos/semgrep", "dados_brutos/sonarqube", "dados_brutos/testes", "resultados/comparativo"):
        (PACKAGE / folder).mkdir(parents=True, exist_ok=True)

    for repo, item in inventory.items():
        slug = repo.replace("/", "__")
        source_human = Path(item["snapshot_path"])
        target_human = PACKAGE / "projetos" / slug / "humano"
        shutil.copytree(source_human, target_human, ignore=ignore, dirs_exist_ok=True)
        prompt = prompts.get(repo, {}).get("prompt", "")
        (PACKAGE / "prompts" / f"{slug}.txt").write_text(prompt, encoding="utf-8")
        for origin in ORIGINS[1:]:
            target = PACKAGE / "projetos" / slug / origin
            target.mkdir(parents=True, exist_ok=True)
            instruction = target / "COLOQUE_O_PROJETO_AQUI.txt"
            if not any(target.glob("*.py")):
                instruction.write_text(
                    f"Coloque aqui o projeto {origin} gerado com o prompt ../../prompts/{slug}.txt.\n",
                    encoding="utf-8",
                )
            metadata = target / "metadata_geracao.json"
            if not metadata.exists():
                metadata.write_text(json.dumps({
                    "repositorio_referencia": repo,
                    "origem": origin,
                    "modelo": "",
                    "versao_modelo": "",
                    "data_geracao": "",
                    "temperatura": "",
                    "execucao": 1,
                    "prompt_arquivo": f"prompts/{slug}.txt",
                    "observacoes": "",
                }, ensure_ascii=False, indent=2), encoding="utf-8")
        for tool in ("semgrep", "sonarqube"):
            old = SOURCE / "reports" / "human" / slug / ("semgrep.json" if tool == "semgrep" else "sonar.json")
            new = PACKAGE / "dados_brutos" / tool / slug / "humano.json"
            if old.exists():
                new.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(old, new)

    fields = [
        "repositorio", "github", "commit_referencia", "link_commit", "origem", "execucao",
        "modelo", "versao_modelo", "data_geracao", "temperatura", "prompt_arquivo",
        "python_loc", "testes_status", "semgrep_status", "semgrep_total", "semgrep_error",
        "semgrep_warning", "semgrep_info", "semgrep_erros_operacionais", "semgrep_cwes",
        "semgrep_por_kloc", "sonarqube_status", "sonarqube_total", "sonarqube_vulnerabilidades",
        "sonarqube_bugs", "sonarqube_code_smells", "sonarqube_hotspots", "sonarqube_severidades",
        "sonarqube_complexidade", "sonarqube_ncloc", "sonarqube_por_kloc", "observacoes",
    ]
    rows = []
    for repo, item in inventory.items():
        slug = repo.replace("/", "__")
        commit = item.get("commit_sha", "")
        for origin in ORIGINS:
            project = PACKAGE / "projetos" / slug / origin
            row = {field: "" for field in fields}
            row.update({
                "repositorio": repo,
                "github": f"https://github.com/{repo}",
                "commit_referencia": commit,
                "link_commit": f"https://github.com/{repo}/commit/{commit}",
                "origem": origin,
                "execucao": 0 if origin == "humano" else 1,
                "modelo": "human" if origin == "humano" else origin,
                "prompt_arquivo": f"prompts/{slug}.txt" if origin != "humano" else "",
                "python_loc": item.get("python_loc", "") if origin == "humano" else python_loc(project),
            })
            semgrep = semgrep_metrics(PACKAGE / "dados_brutos" / "semgrep" / slug / f"{origin}.json")
            sonar = sonar_metrics(PACKAGE / "dados_brutos" / "sonarqube" / slug / f"{origin}.json")
            row.update(semgrep)
            row.update(sonar)
            loc = row.get("python_loc")
            if isinstance(loc, int) and loc > 0:
                if row.get("semgrep_total") != "" and row.get("semgrep_total") is not None:
                    row["semgrep_por_kloc"] = round(float(row["semgrep_total"]) * 1000 / loc, 4)
                if row.get("sonarqube_total") != "" and row.get("sonarqube_total") is not None:
                    row["sonarqube_por_kloc"] = round(float(row["sonarqube_total"]) * 1000 / loc, 4)
            if origin != "humano" and not any(project.rglob("*.py")):
                row["observacoes"] = "aguardando projeto gerado e configuração da API"
            rows.append(row)

    output = PACKAGE / "resultados" / "comparativo" / "tabela_final_humano_x_ia.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    detailed = ROOT / "resultados" / "baseline_humano_detalhado" / "achados_detalhados_semgrep.txt"
    if detailed.exists():
        human_results = PACKAGE / "resultados" / "humano"
        human_results.mkdir(parents=True, exist_ok=True)
        shutil.copy2(detailed, human_results / "relatorio_baseline_humano_detalhado.txt")
    print(output.resolve())


if __name__ == "__main__":
    main()
