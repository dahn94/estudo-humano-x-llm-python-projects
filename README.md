# Vulnerabilidades em código humano vs. código gerado por LLMs

Artefato de reprodução do trabalho **"Comparação de vulnerabilidades em código
desenvolvido por humanos e código gerado por LLMs"** — Qualidade de Software,
Departamento de Informática, Universidade Estadual de Maringá (UEM), 2026.

Autores: Daniel Arruda de Santana, Felipe Fidelis do Nascimento,
Gabriel Valentim de Oliveira Dacie, Luciano Trevisan Alberti.

> Quais diferenças são observadas na quantidade e na densidade de ocorrências
> relacionadas à segurança entre código humano e código gerado por LLMs, quando
> submetidos às ferramentas de análise estática Semgrep e SonarQube?

## Desenho

```
GitHub, Python, ordem de estrelas
 └─ 50 candidatos (critérios automáticos)      configuracao/repositorios.yaml
     └─ 16 finalistas (README lido em pares)   configuracao/repositorios_16_finalistas.yaml
         ├─ CH  último commit até 31/12/2020   projetos/<slug>/humano   (restaurado pelo SHA)
         └─ README + docs + manifestos         prompts/<slug>/prompt_recriacao.txt
             ├─ GPT  GPT-6 Astra               projetos/<slug>/openai
             ├─ CLD  Claude Opus 5.5           projetos/<slug>/claude
             └─ GEM  Gemini 3.8 Flash          projetos/<slug>/gemini
 CH, GPT, CLD, GEM ─> Semgrep + SonarQube, mesma configuração ─> dados_brutos/
                   ─> contagens e densidade por 1.000 linhas    ─> resultados/
```

## Estrutura

```
configuracao/   critérios, coleta bruta (github_top100_raw.json), auditoria da seleção,
                candidatos, finalistas, modelos, ferramentas e regras do Semgrep
prompts/        prompt enviado às LLMs, um por repositório
projetos/       código analisado: humano/ (não versionado) e openai/ claude/ gemini/
dados_brutos/   JSON original do Semgrep e do SonarQube — a evidência do estudo
resultados/     relatório legível por repositório e tabela_final_humano_x_ia.csv
scripts/        o pipeline (abaixo)
compose.yaml    SonarQube, Semgrep e SonarScanner nas versões do estudo
```

## Requisitos

- [uv](https://docs.astral.sh/uv/) — cria o ambiente Python sozinho (`uv run`),
  a partir de `pyproject.toml` e `uv.lock`.
- Docker com Compose — nenhuma ferramenta de análise é instalada na máquina.
- Git.

## Reproduzir

Reproduzir a análise **não exige chamar as LLMs**: o código gerado é entrada
fixa. Gerar de novo tem custo e, como os modelos não são determinísticos,
produziria outro código.

```bash
# 1. código humano de referência, no commit de corte
uv run scripts/restaurar_codigo_humano.py              # 16 finalistas (--todos: 50)

# 2. SonarQube local: sobe o contêiner, troca a senha inicial, grava token em .sonar/
uv run scripts/sonarqube.py preparar

# 3. Semgrep + SonarQube sobre as quatro origens
uv run scripts/analisar.py                             # tudo
uv run scripts/analisar.py psf/requests --origem claude --ferramenta semgrep

# 4. tabela final e relatórios por repositório
uv run scripts/consolidar.py

uv run scripts/sonarqube.py parar
```

`analisar.py` não sobrescreve um JSON que já existe; use `--refazer` para
gerar de novo. A primeira análise baixa as imagens (cerca de 2 GB).

Etapas que antecedem a análise, já executadas e versionadas:

```bash
uv run scripts/selecionar_repositorios.py   # refaz os 50 candidatos (GITHUB_TOKEN opcional)
uv run scripts/gerar_prompts.py             # refaz os prompts a partir do snapshot humano
```

## Configuração das ferramentas

| | |
| --- | --- |
| Semgrep | 1.176.1, regras `configuracao/semgrep-regras.yaml`, `--metrics off --timeout 30 --timeout-threshold 5` |
| SonarQube | Community Build 26.9.0.129388, perfil Sonar way |
| SonarScanner | CLI 8.0.1, `sonar.inclusions=**/*.py`, `sonar.python.version=3` |
| Escopo | só `.py`, sem `.git`, `venv`, `vendor`, `third_party`, `node_modules`, `build`, `dist` |

As mesmas versões e parâmetros valem para as quatro origens. Os resultados das
duas ferramentas não são somados, porque podem apontar a mesma ocorrência.

## Métrica

Densidade = ocorrências ÷ linhas de código Python × 1.000. A normalização
reduz o efeito do tamanho, mas não corrige diferenças de escopo funcional
entre o projeto humano e a reconstrução. Campo vazio na tabela significa "não
executado", nunca zero.

## Seleção dos casos

Critérios automáticos: linguagem principal Python; público, não arquivado, sem
ser fork; criado antes de 01/01/2021; commit até 31/12/2020 23:59:59 UTC;
software executável; pelo menos 500 linhas Python não vazias no commit de
corte; ordem decrescente de estrelas; os 50 primeiros. Inclusões, exclusões e
contagens estão em `configuracao/auditoria_selecao_gitstars.csv`.

Exclusões na leitura em pares (50 → 16): README insuficiente; escala grande
demais para reconstrução por LLM; ML que exige treinamento prévio; uso
contrário às diretrizes éticas dos modelos.

## Código gerado pelas LLMs

Cada implementação vai em `projetos/<slug>/<origem>/` exatamente como o modelo
a entregou, com um `metadata_geracao.json` opcional:

```json
{"modelo": "Claude Opus 5.5", "versao_modelo": "...", "data_geracao": "2026-..", "temperatura": "...", "execucao": 1}
```

## Limitações

Uma geração por modelo; README como especificação; equivalência funcional não
demonstrada; falsos positivos e negativos da análise estática; 16 projetos
Python populares. Ver seção 5 do artigo.
