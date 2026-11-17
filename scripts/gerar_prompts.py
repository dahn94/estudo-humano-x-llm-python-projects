"""Gera, a partir só da documentação pública do snapshot humano, os arquivos
que alimentam as LLMs: análise do README, arquitetura textual e o prompt.

O corpo do código humano não entra no prompt. Requer o código humano restaurado
(scripts/restaurar_codigo_humano.py).

Uso:
    uv run scripts/gerar_prompts.py                 # 16 finalistas
    uv run scripts/gerar_prompts.py psf/requests
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from comum import IGNORADOS, ROOT, selecionar


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
    destino = ROOT / "resultados" / "humano" / repo["slug"]
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
        "ARQUIVOS DOCUMENTAIS UTILIZADOS", *[f"- {p.relative_to(projeto).as_posix()}" for p in (readmes + docs[:30] + manifests)], "",
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
    prompt_dir = ROOT / "prompts" / repo["slug"]
    prompt_dir.mkdir(parents=True, exist_ok=True)
    (prompt_dir / "prompt_recriacao.txt").write_text(prompt, encoding="utf-8")


def main() -> None:
    for repo in selecionar(sys.argv[1:]):
        projeto = ROOT / "projetos" / repo["slug"] / "humano"
        if not any(projeto.glob("README*")):
            sys.exit(f"{repo['nome']}: código humano ausente; rode scripts/restaurar_codigo_humano.py")
        gerar_documentacao(repo, projeto)
        print(f"prompts/{repo['slug']}/prompt_recriacao.txt")


if __name__ == "__main__":
    main()
