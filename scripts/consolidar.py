from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import yaml

import gerar_relatorio_humano


ROOT = Path(__file__).resolve().parent.parent
ORIGENS = ("humano", "openai", "gemini", "claude")


def carregar_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def contar_linhas_python(path: Path) -> int | str:
    arquivos = [
        arquivo for arquivo in path.rglob("*.py")
        if not any(parte in {".git", ".venv", "venv", "__pycache__"} for parte in arquivo.parts)
    ]
    if not arquivos:
        return ""
    return sum(
        sum(1 for linha in arquivo.read_text(encoding="utf-8", errors="ignore").splitlines() if linha.strip())
        for arquivo in arquivos
    )


def metricas_semgrep(path: Path) -> dict:
    payload = carregar_json(path)
    if not payload:
        return {}
    severidades = Counter(x.get("extra", {}).get("severity", "UNKNOWN") for x in payload.get("results", []))
    cwes = Counter()
    for resultado in payload.get("results", []):
        valores = resultado.get("extra", {}).get("metadata", {}).get("cwe", [])
        if isinstance(valores, str):
            valores = [valores]
        cwes.update(valores)
    return {
        "semgrep_status": "concluido" if not payload.get("errors") else "concluido_com_erros",
        "semgrep_total": len(payload.get("results", [])),
        "semgrep_error": severidades.get("ERROR", 0),
        "semgrep_warning": severidades.get("WARNING", 0),
        "semgrep_info": severidades.get("INFO", 0),
        "semgrep_erros_operacionais": len(payload.get("errors", [])),
        "semgrep_cwes": "; ".join(f"{nome} ({quantidade})" for nome, quantidade in sorted(cwes.items())),
    }


def metricas_sonarqube(path: Path) -> dict:
    payload = carregar_json(path)
    if not payload:
        return {}
    issues = payload.get("issues_summary", {}).get("issues", [])
    tipos = Counter(x.get("type", "UNKNOWN") for x in issues)
    severidades = Counter(x.get("severity", "UNKNOWN") for x in issues)
    medidas = {x["metric"]: x.get("value", "") for x in payload.get("component", {}).get("measures", [])}
    return {
        "sonarqube_status": "concluido",
        "sonarqube_total": len(issues),
        "sonarqube_vulnerabilidades": tipos.get("VULNERABILITY", 0),
        "sonarqube_bugs": tipos.get("BUG", 0),
        "sonarqube_code_smells": tipos.get("CODE_SMELL", 0),
        "sonarqube_hotspots": int(medidas.get("security_hotspots", 0) or 0),
        "sonarqube_severidades": "; ".join(f"{nome}={quantidade}" for nome, quantidade in sorted(severidades.items())),
        "sonarqube_complexidade": medidas.get("complexity", ""),
        "sonarqube_ncloc": medidas.get("ncloc", ""),
    }


def main() -> None:
    configuracao = yaml.safe_load((ROOT / "configuracao" / "repositorios.yaml").read_text(encoding="utf-8"))
    campos = [
        "repositorio", "github", "commit_referencia", "link_commit", "origem", "execucao",
        "modelo", "versao_modelo", "data_geracao", "temperatura", "prompt_arquivo",
        "python_loc", "testes_status", "semgrep_status", "semgrep_total", "semgrep_error",
        "semgrep_warning", "semgrep_info", "semgrep_erros_operacionais", "semgrep_cwes",
        "semgrep_por_kloc", "sonarqube_status", "sonarqube_total", "sonarqube_vulnerabilidades",
        "sonarqube_bugs", "sonarqube_code_smells", "sonarqube_hotspots", "sonarqube_severidades",
        "sonarqube_complexidade", "sonarqube_ncloc", "sonarqube_por_kloc", "observacoes",
    ]
    linhas = []
    for repositorio in configuracao["repositorios"]:
        nome = repositorio["nome"]
        slug = nome.replace("/", "__")
        commit = repositorio["commit"]
        for origem in ORIGENS:
            projeto = ROOT / "projetos" / slug / origem
            metadados = carregar_json(projeto / "metadata_geracao.json") if origem != "humano" else {}
            linha = {campo: "" for campo in campos}
            linha.update({
                "repositorio": nome,
                "github": f"https://github.com/{nome}",
                "commit_referencia": commit,
                "link_commit": f"https://github.com/{nome}/commit/{commit}",
                "origem": origem,
                "execucao": 0 if origem == "humano" else metadados.get("execucao", 1),
                "modelo": "human" if origem == "humano" else metadados.get("modelo") or origem,
                "versao_modelo": metadados.get("versao_modelo", ""),
                "data_geracao": metadados.get("data_geracao", ""),
                "temperatura": metadados.get("temperatura", ""),
                "prompt_arquivo": "" if origem == "humano" else f"prompts/{slug}/prompt_recriacao.txt",
                "python_loc": repositorio.get("python_loc_aproximada", "") if origem == "humano" else contar_linhas_python(projeto),
            })
            linha.update(metricas_semgrep(ROOT / "dados_brutos" / "semgrep" / slug / f"{origem}.json"))
            linha.update(metricas_sonarqube(ROOT / "dados_brutos" / "sonarqube" / slug / f"{origem}.json"))
            teste = carregar_json(ROOT / "dados_brutos" / "testes" / slug / f"{origem}.json")
            linha["testes_status"] = teste.get("status", "")
            loc = linha.get("python_loc")
            if isinstance(loc, int) and loc > 0:
                if linha.get("semgrep_total") != "":
                    linha["semgrep_por_kloc"] = round(linha["semgrep_total"] * 1000 / loc, 4)
                if linha.get("sonarqube_total") != "":
                    linha["sonarqube_por_kloc"] = round(linha["sonarqube_total"] * 1000 / loc, 4)
            if origem != "humano" and not any(projeto.rglob("*.py")):
                linha["observacoes"] = "aguardando projeto gerado"
            else:
                linha["observacoes"] = metadados.get("observacoes", "")
            linhas.append(linha)

    destino = ROOT / "resultados" / "tabela_final_humano_x_ia.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)
    print(destino.relative_to(ROOT))
    gerar_relatorio_humano.main()


if __name__ == "__main__":
    main()
