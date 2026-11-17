from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "resultados" / "humano"


def limpar_caminho(valor: str) -> str:
    valor = valor.replace("\\", "/")
    marcador = "workspace/repository_study/human/"
    if marcador in valor:
        valor = valor.split(marcador, 1)[1]
    partes = valor.split("/", 1)
    if len(partes) == 2 and "__" in partes[0]:
        return partes[1]
    return valor


def lista_cwes(resultados: list[dict]) -> Counter:
    contador = Counter()
    for resultado in resultados:
        cwes = resultado.get("extra", {}).get("metadata", {}).get("cwe", [])
        if isinstance(cwes, str):
            cwes = [cwes]
        contador.update(cwes)
    return contador


def linha(char: str = "=", largura: int = 100) -> str:
    return char * largura


def main() -> None:
    configuracao = yaml.safe_load((ROOT / "configuracao" / "repositorios.yaml").read_text(encoding="utf-8"))
    for indice, repositorio in enumerate(configuracao["repositorios"], 1):
        nome = repositorio["nome"]
        slug = nome.replace("/", "__")
        commit = repositorio["commit"]
        github = f"https://github.com/{nome}"
        semgrep_path = ROOT / "dados_brutos" / "semgrep" / slug / "humano.json"
        sonar_path = ROOT / "dados_brutos" / "sonarqube" / slug / "humano.json"
        if not semgrep_path.exists() or not sonar_path.exists():
            destino = OUTPUT_DIR / slug / "relatorio_scan_humano.txt"
            destino.parent.mkdir(parents=True, exist_ok=True)
            faltantes = [
                str(path.relative_to(ROOT)).replace("\\", "/")
                for path in (semgrep_path, sonar_path)
                if not path.exists()
            ]
            destino.write_text(
                "\n".join([
                    linha("="),
                    "RELATORIO DO BASELINE HUMANO - AGUARDANDO SCANS",
                    linha("="),
                    "",
                    f"GitHub: {nome}",
                    f"Repositorio: {github}",
                    f"Commit analisado: {commit}",
                    f"Link do commit: {github}/commit/{commit}",
                    "Status: AGUARDANDO SEMGREP E/OU SONARQUBE",
                    "",
                    "Arquivos ainda nao encontrados:",
                    *[f"  - {path}" for path in faltantes],
                    "",
                    "Campos ausentes nao representam zero achado.",
                ]),
                encoding="utf-8",
            )
            print(destino.resolve())
            continue
        semgrep = json.loads(semgrep_path.read_text(encoding="utf-8"))
        sonar = json.loads(sonar_path.read_text(encoding="utf-8"))
        resultados_semgrep = semgrep.get("results", [])
        erros_semgrep = semgrep.get("errors", [])
        issues_sonar = sonar.get("issues_summary", {}).get("issues", [])
        severidades_semgrep = Counter(x.get("extra", {}).get("severity", "UNKNOWN") for x in resultados_semgrep)
        tipos_sonar = Counter(x.get("type", "UNKNOWN") for x in issues_sonar)
        severidades_sonar = Counter(x.get("severity", "UNKNOWN") for x in issues_sonar)
        cwes = lista_cwes(resultados_semgrep)
        medidas = {x["metric"]: x.get("value", "") for x in sonar.get("component", {}).get("measures", [])}

        saida = [
            linha("="),
            "RELATORIO DO BASELINE HUMANO - SEMGREP E SONARQUBE",
            linha("="),
            "",
            f"Repositorio {indice} da configuracao atual.",
            "Este arquivo contem somente os resultados deste GitHub.",
            "Os resultados do Semgrep e SonarQube nao devem ser somados, pois podem apontar o mesmo problema.",
            "",
            linha("#"),
            f"GITHUB: {nome}",
            linha("#"),
            f"Repositorio: {github}",
            f"Commit analisado: {commit}",
            f"Link do commit: {github}/commit/{commit}",
            f"Grupo metodologico: {repositorio.get('grupo', '')}",
            f"Linhas Python aproximadas: {repositorio.get('python_loc_aproximada', '')}",
            "",
            linha("-"),
            "RESUMO DESTE REPOSITORIO",
            linha("-"),
            "",
            "SEMGREP",
            f"  Total de achados: {len(resultados_semgrep)}",
            f"  ERROR: {severidades_semgrep.get('ERROR', 0)}",
            f"  WARNING: {severidades_semgrep.get('WARNING', 0)}",
            f"  INFO: {severidades_semgrep.get('INFO', 0)}",
            f"  Erros operacionais: {len(erros_semgrep)}",
            "",
            "SONARQUBE",
            f"  Total de issues: {len(issues_sonar)}",
            f"  Vulnerabilidades: {tipos_sonar.get('VULNERABILITY', 0)}",
            f"  Bugs: {tipos_sonar.get('BUG', 0)}",
            f"  Code smells: {tipos_sonar.get('CODE_SMELL', 0)}",
            f"  Security hotspots: {medidas.get('security_hotspots', 0)}",
            f"  Complexidade: {medidas.get('complexity', '')}",
            f"  Linhas analisadas pelo SonarQube: {medidas.get('ncloc', '')}",
            "  Severidades: " + (", ".join(f"{k}={v}" for k, v in sorted(severidades_sonar.items())) or "nenhuma"),
            "",
            "CWEs ENCONTRADAS PELO SEMGREP",
        ]
        if cwes:
            saida.extend(f"  - {cwe}: {quantidade} ocorrencia(s)" for cwe, quantidade in sorted(cwes.items()))
        else:
            saida.append("  Nenhuma CWE informada.")

        saida.extend(["", linha("-"), "SCAN 1 - SEMGREP: DETALHAMENTO", linha("-"), ""])
        for numero, achado in enumerate(resultados_semgrep, 1):
            extra = achado.get("extra", {})
            caminho = limpar_caminho(achado.get("path", ""))
            numero_linha = achado.get("start", {}).get("line", "")
            cwe_achado = extra.get("metadata", {}).get("cwe", [])
            if isinstance(cwe_achado, str):
                cwe_achado = [cwe_achado]
            link = f"{github}/blob/{commit}/{caminho}" + (f"#L{numero_linha}" if numero_linha else "")
            saida.extend([
                f"[SEMGREP {numero}]",
                f"Severidade: {extra.get('severity', 'UNKNOWN')}",
                f"Regra: {achado.get('check_id', '')}",
                f"CWE: {'; '.join(cwe_achado) or 'nao informada'}",
                f"Arquivo: {caminho}",
                f"Linha: {numero_linha or 'nao informada'}",
                f"Link do codigo: {link}",
                f"Descricao: {extra.get('message', '').replace(chr(10), ' ')}",
                "",
            ])

        saida.extend(["ERROS OPERACIONAIS DO SEMGREP"])
        if not erros_semgrep:
            saida.append("Nenhum.")
        for erro in erros_semgrep:
            saida.extend([
                f"Tipo: {erro.get('type', '')}",
                f"Nivel: {erro.get('level', '')}",
                f"Regra: {erro.get('rule_id', '')}",
                f"Arquivo: {limpar_caminho(erro.get('path', ''))}",
                "Observacao: erro do scanner; nao contabilizado como vulnerabilidade.",
                "",
            ])

        saida.extend(["", linha("-"), "SCAN 2 - SONARQUBE: DETALHAMENTO", linha("-"), ""])
        for numero, issue in enumerate(issues_sonar, 1):
            componente = issue.get("component", "")
            caminho = componente.split(":", 1)[1] if ":" in componente else componente
            numero_linha = issue.get("line", "")
            link = f"{github}/blob/{commit}/{caminho}" + (f"#L{numero_linha}" if numero_linha else "")
            saida.extend([
                f"[SONARQUBE {numero}]",
                f"Tipo: {issue.get('type', 'nao informado')}",
                f"Severidade: {issue.get('severity', 'nao informada')}",
                f"Regra: {issue.get('rule', '')}",
                "CWE: nao fornecida diretamente no JSON consultado",
                f"Arquivo: {caminho}",
                f"Linha: {numero_linha or 'nao informada'}",
                f"Link do codigo: {link}",
                f"Descricao: {issue.get('message', '')}",
                "",
            ])

        saida.extend([
            linha("-"),
            f"FIM DO RELATORIO DE {nome}",
            "Classificacao: COM ACHADOS",
            linha("-"),
            "",
        ])

        destino = OUTPUT_DIR / slug / "relatorio_scan_humano.txt"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text("\n".join(saida), encoding="utf-8")
        print(destino.resolve())


if __name__ == "__main__":
    main()
