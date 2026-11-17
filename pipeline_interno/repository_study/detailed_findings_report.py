from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / "workspace" / "repository_study"
OUTPUT = ROOT / "resultados" / "03_detalhado_semgrep" / "achados_detalhados_semgrep.txt"
BASELINE_SEMGREP = ROOT / "resultados" / "01_resumo_semgrep" / "baseline_humano_semgrep.txt"
BASELINE_COMBINED = ROOT / "resultados" / "02_resumo_semgrep_sonarqube" / "baseline_humano_semgrep_sonarqube.txt"


def clean_path(value: str) -> str:
    marker = "workspace/repository_study/human/"
    cleaned = value.split(marker, 1)[-1] if marker in value else value
    parts = cleaned.replace("\\", "/").split("/", 1)
    return parts[1] if len(parts) == 2 and "__" in parts[0] else cleaned


def main() -> None:
    summaries = {
        item["repo"]: item
        for item in (
            json.loads(line)
            for line in (WORKSPACE / "security_summary.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    inventory = {
        item["repo"]: item
        for item in (
            json.loads(line)
            for line in (WORKSPACE / "inventory.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    lines = [
        "ACHADOS DETALHADOS — SEMGREP OFICIAL",
        "====================================",
        "",
        "Legenda:",
        "- ERROR, WARNING e INFO são severidades atribuídas às regras do Semgrep.",
        "- ERROR indica um achado de maior severidade; não significa falha do programa.",
        "- WARNING indica risco que exige revisão e confirmação manual.",
        "- INFO indica achado informativo ou de menor confiança/impacto.",
        "- Erros do scanner, como timeout, aparecem separadamente e não são achados.",
        "",
    ]
    for repo, summary in summaries.items():
        slug = repo.replace("/", "__")
        report_path = WORKSPACE / "reports" / "human" / slug / "semgrep.json"
        if not report_path.exists():
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        inv = inventory.get(repo, {})
        commit = inv.get("commit_sha", "")
        github_url = f"https://github.com/{repo}"
        lines.extend([
            repo,
            "-" * len(repo),
            f"Ferramenta: Semgrep OSS {summary.get('semgrep_version', '')}",
            f"Repositório GitHub: {github_url}",
            f"Commit utilizado: {commit}",
            f"Link do commit: {github_url}/commit/{commit}",
            f"Linhas Python aproximadas: {summary.get('python_loc', '')}",
            f"Total de achados: {len(report.get('results', []))}",
            "",
        ])
        for number, finding in enumerate(report.get("results", []), 1):
            extra = finding.get("extra", {})
            source_path = clean_path(finding.get("path", ""))
            source_line = finding.get("start", {}).get("line", "")
            cwe = extra.get("metadata", {}).get("cwe", [])
            if isinstance(cwe, str):
                cwe = [cwe]
            lines.extend([
                f"ACHADO {number}",
                f"Ferramenta: Semgrep",
                f"Severidade: {extra.get('severity', 'UNKNOWN')}",
                f"Regra: {finding.get('check_id', '')}",
                f"Arquivo: {source_path}",
                f"Linha: {source_line}",
                f"Link do código no commit: {github_url}/blob/{commit}/{source_path}#L{source_line}",
                f"CWE: {'; '.join(cwe) or 'não informada'}",
                f"Descrição: {extra.get('message', '').replace(chr(10), ' ')}",
                "",
            ])
        errors = report.get("errors", [])
        lines.append("ERROS OPERACIONAIS DO SCANNER")
        if not errors:
            lines.append("Nenhum.")
        for error in errors:
            lines.extend([
                f"Tipo: {error.get('type', '')}",
                f"Nível: {error.get('level', '')}",
                f"Regra: {error.get('rule_id', '')}",
                f"Arquivo: {clean_path(error.get('path', ''))}",
                "Impacto: a regra não terminou nesse arquivo; isto não é um achado de vulnerabilidade.",
            ])
        lines.extend(["", "Classificação do projeto: COM ACHADOS", "", ""])
    for output_dir in {OUTPUT.parent, BASELINE_SEMGREP.parent, BASELINE_COMBINED.parent}:
        output_dir.mkdir(parents=True, exist_ok=True)
    semgrep_text = "\n".join(lines)
    OUTPUT.write_text(semgrep_text, encoding="utf-8")

    semgrep_summary = [
        "BASELINE HUMANO — RESUMO GERAL DO SEMGREP",
        "==========================================",
        "",
        "ERROR, WARNING e INFO são severidades de achados do Semgrep.",
        "Timeouts são erros operacionais e não entram no total de achados.",
        "",
    ]
    combined = [
        "BASELINE HUMANO — RESUMO SEMGREP + SONARQUBE",
        "=============================================",
        "",
        "Os totais das ferramentas são apresentados separadamente e não devem ser somados.",
        "SonarQube foi executado somente sobre arquivos Python (**/*.py).",
        "",
    ]
    for repo, summary in summaries.items():
        slug = repo.replace("/", "__")
        semgrep_path = WORKSPACE / "reports" / "human" / slug / "semgrep.json"
        report_path = WORKSPACE / "reports" / "human" / slug / "sonar.json"
        if not semgrep_path.exists():
            continue
        semgrep = json.loads(semgrep_path.read_text(encoding="utf-8"))
        severity_counts = Counter(
            item.get("extra", {}).get("severity", "UNKNOWN") for item in semgrep.get("results", [])
        )
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        inv = inventory.get(repo, {})
        commit = inv.get("commit_sha", "")
        github_url = f"https://github.com/{repo}"
        issues = payload.get("issues_summary", {}).get("issues", [])
        project_summary = [
            repo,
            "-" * len(repo),
            f"Repositório GitHub: {github_url}",
            f"Commit utilizado: {commit}",
            f"Link do commit: {github_url}/commit/{commit}",
            f"Linhas Python aproximadas: {summary.get('python_loc', '')}",
            f"Semgrep — total: {len(semgrep.get('results', []))}",
            f"Semgrep — ERROR: {severity_counts.get('ERROR', 0)}",
            f"Semgrep — WARNING: {severity_counts.get('WARNING', 0)}",
            f"Semgrep — INFO: {severity_counts.get('INFO', 0)}",
            f"Semgrep — erros operacionais: {len(semgrep.get('errors', []))}",
            "",
        ]
        semgrep_summary.extend(project_summary)
        type_counts = Counter(item.get("type", "UNKNOWN") for item in issues)
        severity_sonar = Counter(item.get("severity", "UNKNOWN") for item in issues)
        combined.extend(project_summary[:-1])
        combined.extend([
            f"SonarQube — total de issues: {len(issues)}",
            f"SonarQube — vulnerabilidades: {type_counts.get('VULNERABILITY', 0)}",
            f"SonarQube — bugs: {type_counts.get('BUG', 0)}",
            f"SonarQube — code smells: {type_counts.get('CODE_SMELL', 0)}",
            "SonarQube — severidades: " + ", ".join(f"{key}={value}" for key, value in sorted(severity_sonar.items())),
            "Classificação: COM ACHADOS",
            "",
            "",
        ])
    BASELINE_SEMGREP.write_text("\n".join(semgrep_summary), encoding="utf-8")
    BASELINE_COMBINED.write_text("\n".join(combined), encoding="utf-8")
    print(OUTPUT.resolve())
    print(BASELINE_SEMGREP.resolve())
    print(BASELINE_COMBINED.resolve())


if __name__ == "__main__":
    main()
