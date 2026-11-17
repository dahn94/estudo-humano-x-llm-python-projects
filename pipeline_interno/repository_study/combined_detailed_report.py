from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / "workspace" / "repository_study"
OUTPUT = ROOT / "resultados" / "baseline_humano_detalhado" / "achados_detalhados_semgrep.txt"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def semgrep_path(raw_path: str) -> str:
    marker = "workspace/repository_study/human/"
    value = raw_path.replace("\\", "/")
    if marker in value:
        value = value.split(marker, 1)[1]
    parts = value.split("/", 1)
    return parts[1] if len(parts) == 2 and "__" in parts[0] else value


def main() -> None:
    inventory = {item["repo"]: item for item in load_jsonl(WORKSPACE / "inventory.jsonl")}
    summaries = {item["repo"]: item for item in load_jsonl(WORKSPACE / "security_summary.jsonl")}
    overview = []
    global_semgrep = Counter()
    global_sonar_types = Counter()
    global_sonar_severities = Counter()
    global_cwes = Counter()
    global_scanner_errors = 0
    for repo in summaries:
        slug = repo.replace("/", "__")
        semgrep = json.loads((WORKSPACE / "reports" / "human" / slug / "semgrep.json").read_text(encoding="utf-8"))
        sonar = json.loads((WORKSPACE / "reports" / "human" / slug / "sonar.json").read_text(encoding="utf-8"))
        semgrep_severities = Counter(
            finding.get("extra", {}).get("severity", "UNKNOWN") for finding in semgrep.get("results", [])
        )
        semgrep_cwes = Counter()
        for finding in semgrep.get("results", []):
            cwes = finding.get("extra", {}).get("metadata", {}).get("cwe", [])
            if isinstance(cwes, str):
                cwes = [cwes]
            semgrep_cwes.update(cwes)
        sonar_issues = sonar.get("issues_summary", {}).get("issues", [])
        sonar_types = Counter(issue.get("type", "UNKNOWN") for issue in sonar_issues)
        sonar_severities = Counter(issue.get("severity", "UNKNOWN") for issue in sonar_issues)
        scanner_errors = len(semgrep.get("errors", []))
        global_semgrep.update(semgrep_severities)
        global_sonar_types.update(sonar_types)
        global_sonar_severities.update(sonar_severities)
        global_cwes.update(semgrep_cwes)
        global_scanner_errors += scanner_errors
        overview.append((
            repo, len(semgrep.get("results", [])), semgrep_severities, scanner_errors,
            len(sonar_issues), sonar_types, sonar_severities, semgrep_cwes,
        ))
    lines = [
        "BASELINE HUMANO — ACHADOS DETALHADOS DO SEMGREP E SONARQUBE",
        "============================================================",
        "",
        "RESUMO GERAL",
        "============",
        "",
        f"Repositórios analisados: {len(overview)}",
        f"Semgrep — total de achados: {sum(global_semgrep.values())}",
        f"Semgrep — ERROR: {global_semgrep.get('ERROR', 0)}",
        f"Semgrep — WARNING: {global_semgrep.get('WARNING', 0)}",
        f"Semgrep — INFO: {global_semgrep.get('INFO', 0)}",
        f"Semgrep — erros operacionais: {global_scanner_errors}",
        f"SonarQube — total de issues: {sum(global_sonar_types.values())}",
        f"SonarQube — vulnerabilidades: {global_sonar_types.get('VULNERABILITY', 0)}",
        f"SonarQube — bugs: {global_sonar_types.get('BUG', 0)}",
        f"SonarQube — code smells: {global_sonar_types.get('CODE_SMELL', 0)}",
        "SonarQube — severidades: " + ", ".join(
            f"{name}={count}" for name, count in sorted(global_sonar_severities.items())
        ),
        "",
        "CWEs encontradas pelo Semgrep:",
        *[f"- {name}: {count} ocorrência(s)" for name, count in sorted(global_cwes.items())],
        "SonarQube — CWE: não fornecida diretamente na resposta bruta de issues consultada.",
        "",
        "RESUMO POR REPOSITÓRIO",
        "=======================",
        "",
    ]
    for repo, semgrep_total, semgrep_severities, scanner_errors, sonar_total, sonar_types, sonar_severities, semgrep_cwes in overview:
        commit = inventory.get(repo, {}).get("commit_sha", "")
        github = f"https://github.com/{repo}"
        lines.extend([
            f"Repositório: {repo}",
            f"GitHub: {github}",
            f"Commit utilizado: {commit}",
            f"Link do commit: {github}/commit/{commit}",
            f"Semgrep: {semgrep_total} achados — ERROR={semgrep_severities.get('ERROR', 0)}, "
            f"WARNING={semgrep_severities.get('WARNING', 0)}, INFO={semgrep_severities.get('INFO', 0)}; "
            f"erros operacionais={scanner_errors}",
            f"SonarQube: {sonar_total} issues — vulnerabilidades={sonar_types.get('VULNERABILITY', 0)}, "
            f"bugs={sonar_types.get('BUG', 0)}, code smells={sonar_types.get('CODE_SMELL', 0)}",
            "SonarQube — severidades: " + ", ".join(
                f"{name}={count}" for name, count in sorted(sonar_severities.items())
            ),
            "CWEs do Semgrep: " + "; ".join(
                f"{name} ({count})" for name, count in sorted(semgrep_cwes.items())
            ),
            "CWE do SonarQube: não fornecida diretamente no relatório bruto consultado",
            "Classificação: COM ACHADOS",
            "",
        ])
    lines.extend([
        "DETALHAMENTO COMPLETO",
        "======================",
        "",
        "Cada achado identifica a ferramenta, regra, severidade, arquivo, linha e código no commit analisado.",
        "CWE é exibida quando a ferramenta a fornece no relatório bruto.",
        "Os achados das duas ferramentas não devem ser somados, pois podem representar o mesmo problema.",
        "",
    ])
    for repo, summary in summaries.items():
        slug = repo.replace("/", "__")
        commit = inventory.get(repo, {}).get("commit_sha", "")
        github = f"https://github.com/{repo}"
        semgrep = json.loads((WORKSPACE / "reports" / "human" / slug / "semgrep.json").read_text(encoding="utf-8"))
        sonar = json.loads((WORKSPACE / "reports" / "human" / slug / "sonar.json").read_text(encoding="utf-8"))
        lines.extend([
            "#" * 72,
            f"REPOSITÓRIO: {repo}",
            f"GitHub: {github}",
            f"Commit utilizado: {commit}",
            f"Link do commit: {github}/commit/{commit}",
            f"Linhas Python aproximadas: {summary.get('python_loc', '')}",
            "#" * 72,
            "",
            "--------------------------- // SEMGREP // ---------------------------",
            "",
            f"Total de achados do Semgrep: {len(semgrep.get('results', []))}",
            "",
        ])
        for number, finding in enumerate(semgrep.get("results", []), 1):
            extra = finding.get("extra", {})
            metadata = extra.get("metadata", {})
            cwe = metadata.get("cwe", [])
            if isinstance(cwe, str):
                cwe = [cwe]
            path = semgrep_path(finding.get("path", ""))
            line = finding.get("start", {}).get("line", "")
            lines.extend([
                f"ACHADO SEMGREP {number}",
                "Ferramenta: Semgrep",
                f"Severidade: {extra.get('severity', 'UNKNOWN')}",
                f"Regra: {finding.get('check_id', '')}",
                f"CWE: {'; '.join(cwe) or 'não informada pelo Semgrep'}",
                f"Arquivo: {path}",
                f"Linha: {line or 'não informada'}",
                f"Link do código: {github}/blob/{commit}/{path}" + (f"#L{line}" if line else ""),
                f"Descrição: {extra.get('message', '').replace(chr(10), ' ')}",
                "",
            ])
        lines.append("ERROS OPERACIONAIS DO SEMGREP")
        if not semgrep.get("errors"):
            lines.append("Nenhum.")
        for error in semgrep.get("errors", []):
            lines.extend([
                f"Tipo: {error.get('type', '')}",
                f"Nível: {error.get('level', '')}",
                f"Regra: {error.get('rule_id', '')}",
                f"Arquivo: {semgrep_path(error.get('path', ''))}",
                "Observação: falha operacional do scanner; não contabilizada como vulnerabilidade.",
            ])

        issues = sonar.get("issues_summary", {}).get("issues", [])
        lines.extend([
            "",
            "-------------------------- // SONARQUBE // --------------------------",
            "",
            "Escopo: somente arquivos Python (**/*.py)",
            f"Total de issues do SonarQube: {len(issues)}",
            "",
        ])
        for number, issue in enumerate(issues, 1):
            component = issue.get("component", "")
            path = component.split(":", 1)[1] if ":" in component else component
            line = issue.get("line", "")
            lines.extend([
                f"ACHADO SONARQUBE {number}",
                "Ferramenta: SonarQube",
                f"Tipo: {issue.get('type', 'não informado')}",
                f"Severidade: {issue.get('severity', 'não informada')}",
                f"Regra: {issue.get('rule', '')}",
                "CWE: não informada no relatório bruto consultado",
                f"Arquivo: {path}",
                f"Linha: {line or 'não informada'}",
                f"Link do código: {github}/blob/{commit}/{path}" + (f"#L{line}" if line else ""),
                f"Descrição: {issue.get('message', '')}",
                "",
            ])
        lines.extend(["CLASSIFICAÇÃO DO PROJETO: COM ACHADOS", "", ""])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT.resolve())


if __name__ == "__main__":
    main()
