from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
IGNORADOS = {".git", ".venv", "venv", "node_modules", "vendor", "vendors", "third_party", "third-party", "build", "dist", "__pycache__"}


def executar(cmd: list[str], cwd: Path | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)


def git(args: list[str], cwd: Path) -> None:
    proc = executar(["git", "-c", "http.sslBackend=openssl", "-c", "core.longpaths=true", *args], cwd, 1800)
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout)[-4000:])


def preparar(repo: dict) -> Path:
    destino = ROOT / "projetos" / repo["slug"] / "humano"
    destino.mkdir(parents=True, exist_ok=True)
    if not (destino / ".git").exists():
        git(["init"], destino)
        git(["remote", "add", "origin", repo["github"] + ".git"], destino)
    git(["fetch", "--depth", "1", "--filter=blob:none", "origin", repo["commit"]], destino)
    git(["sparse-checkout", "init", "--no-cone"], destino)
    padroes = ["*.py", "README*", "docs/**/*.md", "docs/**/*.rst", "*.md", "*.rst", "pyproject.toml", "setup.py", "setup.cfg", "requirements*.txt", "Pipfile", "tox.ini"]
    git(["sparse-checkout", "set", "--no-cone", *padroes], destino)
    git(["checkout", "--force", "--detach", "FETCH_HEAD"], destino)
    return destino


def arquivos_validos(root: Path, padrao: str) -> list[Path]:
    return [p for p in root.rglob(padrao) if not ({x.lower() for x in p.relative_to(root).parts} & IGNORADOS)]


def ler_limitado(paths: list[Path], limite: int) -> str:
    partes, usados = [], 0
    for path in paths:
        texto = path.read_text(encoding="utf-8", errors="ignore")
        restante = limite - usados
        if restante <= 0:
            break
        trecho = texto[:restante]
        partes.append(f"\n--- {path.name} ---\n{trecho}")
        usados += len(trecho)
    return "".join(partes)


def titulos(texto: str) -> list[str]:
    valores = []
    for linha in texto.splitlines():
        limpa = re.sub(r"[`*_#>-]", "", linha).strip()
        if linha.lstrip().startswith("#") and 2 <= len(limpa) <= 100:
            valores.append(limpa)
        elif re.match(r"^[A-Za-z][A-Za-z0-9 /&_.:-]{3,80}$", limpa) and limpa.lower() in {"installation", "usage", "features", "documentation", "quick start", "getting started", "configuration", "requirements", "examples", "testing", "instalacao", "uso", "recursos"}:
            valores.append(limpa)
    return list(dict.fromkeys(valores))[:30]


def arvore_textual(root: Path) -> str:
    dirs = sorted({p.relative_to(root).parts[0] for p in root.iterdir() if p.is_dir() and p.name != ".git"})[:20]
    arquivos = sorted(p.name for p in root.iterdir() if p.is_file())[:20]
    linhas = ["PROJETO", "|", "+-- Documentacao e configuracao"]
    for nome in arquivos:
        linhas.append(f"|   +-- {nome}")
    linhas.append("|\n+-- Modulos/dominios visiveis")
    for nome in dirs:
        linhas.append(f"|   +-- {nome}/")
    linhas.extend(["|", "+-- Entradas e interfaces descritas no README", "|   +-- configuracao/parametros", "|   +-- processamento principal", "|   +-- saidas/resultados", "|", "+-- Testes proprios a serem criados pela IA"])
    return "\n".join(linhas)


def gerar_documentacao(repo: dict, projeto: Path) -> None:
    destino = ROOT / "resultados" / "resultados_scan_humano" / repo["slug"]
    destino.mkdir(parents=True, exist_ok=True)
    readmes = sorted([p for p in projeto.glob("README*") if p.is_file()])
    docs = sorted(arquivos_validos(projeto / "docs", "*.md") + arquivos_validos(projeto / "docs", "*.rst")) if (projeto / "docs").exists() else []
    manifests = [p for nome in ("pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "tox.ini") for p in projeto.glob(nome)] + list(projeto.glob("requirements*.txt"))
    readme = ler_limitado(readmes, 50000)
    doc = ler_limitado(docs, 30000)
    manifest = ler_limitado(manifests, 15000)
    secoes = titulos(readme)
    analise = [
        "O QUE E ESTE ARQUIVO", "=" * 80,
        "Este arquivo apresenta a analise documental do repositorio, produzida a partir do README,",
        "da documentacao publica, dos manifestos e dos nomes da estrutura. Ele serve para o time",
        "conferir o que foi entendido sobre o software antes de envia-lo a uma IA.",
        "Nao e um resultado de vulnerabilidades e nao contem o corpo do codigo-fonte humano.", "",
        "ANALISE DOCUMENTAL DO SOFTWARE", "=" * 80, "",
        f"GitHub: {repo['nome']}", f"Repositorio: {repo['github']}", f"Commit: {repo['commit']}",
        f"Data do commit: {repo['commit_date']}", f"Link: {repo['github']}/tree/{repo['commit']}", "",
        "ESCOPO E METODO", "Esta analise foi produzida somente a partir de README, documentacao publica, manifestos e nomes da estrutura.",
        "O corpo do codigo-fonte humano nao foi usado para construir a especificacao ou o prompt.", "",
        "SECOES IDENTIFICADAS NO README",
        *([f"- {x}" for x in secoes] or ["- Nenhum titulo Markdown reconhecido automaticamente."]), "",
        "ARQUIVOS DOCUMENTAIS UTILIZADOS", *[f"- {p.relative_to(projeto)}" for p in (readmes + docs[:30] + manifests)], "",
        "INTERPRETACAO", "O sistema a ser recriado deve preservar apenas capacidades e interfaces descritas publicamente. Detalhes ausentes devem ser resolvidos com implementacao nova, segura e testavel.",
    ]
    (destino / "01_analise_readme.txt").write_text("\n".join(analise), encoding="utf-8")
    desenho = ["O QUE E ESTE ARQUIVO", "=" * 80,
        "Este arquivo e um desenho textual da estrutura e do fluxo funcional esperados para o projeto.",
        "Ele foi inferido somente da documentacao publica e ajuda a IA e o time a visualizar os",
        "componentes principais. Nao representa necessariamente a arquitetura interna real do codigo",
        "humano e deve ser validado antes do experimento.", "",
        "DESENHO TEXTUAL INFERIDO DA DOCUMENTACAO", "=" * 80, "", "Legenda: estrutura inferida; deve ser validada pelo time antes do experimento.", "", arvore_textual(projeto), "", "FLUXO FUNCIONAL", "", "Usuario/cliente", "    |", "    v", "Interface publica descrita no README", "    |", "    v", "Validacao e configuracao", "    |", "    v", "Logica funcional recriada pela IA", "    |", "    v", "Saidas descritas + logs + tratamento de erros"]
    (destino / "02_arquitetura_textual.txt").write_text("\n".join(desenho), encoding="utf-8")
    prompt = f"""O QUE E ESTE ARQUIVO
================================================================================
Este e o prompt que deve ser enviado ao ChatGPT, Gemini ou Claude para recriar o projeto.
Ele contem somente informacoes documentais publicas e a arquitetura textual inferida; o corpo do
codigo-fonte humano nao foi incluido. A resposta da IA devera ser salva separadamente e depois
avaliada pelas mesmas ferramentas Semgrep e SonarQube usadas no projeto humano.

INSTRUCAO PARA A IA
================================================================================
Crie do zero um projeto Python funcionalmente semelhante ao descrito abaixo.
REGRAS OBRIGATORIAS:
- Nao procure, copie, traduza ou reproduza o codigo-fonte do repositorio original.
- Use apenas README, documentacao e manifestos fornecidos neste prompt.
- Implemente as funcionalidades publicas documentadas, validacao de entrada, tratamento de erros e testes proprios.
- Nao inclua segredos, credenciais, caminhos absolutos ou dependencias desnecessarias.
- Entregue todos os arquivos completos e um README de execucao.

REFERENCIA: {repo['nome']}
COMMIT DOCUMENTAL: {repo['commit']}

README:
{readme}

DOCUMENTACAO PUBLICA:
{doc}

MANIFESTOS PUBLICOS:
{manifest}

ARQUITETURA TEXTUAL INFERIDA:
{arvore_textual(projeto)}
"""
    (destino / "03_prompt_recriacao_ia.txt").write_text(prompt, encoding="utf-8")
    prompt_dir = ROOT / "prompts" / repo["slug"]
    prompt_dir.mkdir(parents=True, exist_ok=True)
    (prompt_dir / "prompt_recriacao.txt").write_text(prompt, encoding="utf-8")


def scan(repo: dict) -> None:
    chave = "human-" + re.sub(r"[^a-z0-9_-]", "-", repo["slug"].lower())[:180]
    proc = executar(["wsl.exe", "-d", "Ubuntu", "--cd", str(ROOT), "bash", "pipeline_interno/scan_repo_wsl.sh", repo["slug"], chave], ROOT, 7200)
    log = ROOT / "resultados" / "resultados_scan_humano" / repo["slug"] / "logs_tecnicos" / "execucao_scan.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(f"exit_code={proc.returncode}\n\nSTDOUT\n{proc.stdout}\n\nSTDERR\n{proc.stderr}", encoding="utf-8")
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout)[-4000:])


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--inicio", type=int, default=1)
    parser.add_argument("--fim", type=int, default=50)
    parser.add_argument("--pular-prontos", action="store_true")
    args = parser.parse_args()
    cfg = yaml.safe_load((ROOT / "configuracao" / "repositorios.yaml").read_text(encoding="utf-8"))
    repos = cfg["repositorios"][args.inicio - 1:args.fim]
    status_path = ROOT / "resultados" / "progresso_scans_humanos.jsonl"
    for numero, repo in enumerate(repos, args.inicio):
        sonar = ROOT / "dados_brutos" / "sonarqube" / repo["slug"] / "humano.json"
        semgrep = ROOT / "dados_brutos" / "semgrep" / repo["slug"] / "humano.json"
        if args.pular_prontos and sonar.exists() and semgrep.exists():
            print(f"[{numero}/50] PRONTO {repo['nome']}", flush=True)
            continue
        inicio = datetime.now(timezone.utc)
        registro = {"indice": numero, "repo": repo["nome"], "slug": repo["slug"], "inicio": inicio.isoformat()}
        try:
            print(f"[{numero}/50] PREPARANDO {repo['nome']}", flush=True)
            projeto = preparar(repo)
            gerar_documentacao(repo, projeto)
            print(f"[{numero}/50] SCANS {repo['nome']}", flush=True)
            scan(repo)
            registro["status"] = "concluido"
            print(f"[{numero}/50] CONCLUIDO {repo['nome']}", flush=True)
        except Exception as exc:
            registro.update({"status": "erro", "erro": str(exc)})
            print(f"[{numero}/50] ERRO {repo['nome']}: {exc}", flush=True)
        registro["fim"] = datetime.now(timezone.utc).isoformat()
        with status_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(registro, ensure_ascii=False) + "\n")

    executar([sys.executable, str(ROOT / "scripts" / "gerar_relatorio_humano.py")], ROOT, 600)


if __name__ == "__main__":
    main()
