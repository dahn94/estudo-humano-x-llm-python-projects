# Vulnerabilidades em código humano vs. código gerado por LLMs

Artefato de reprodução do trabalho **"Comparação de vulnerabilidades em código
desenvolvido por humanos e código gerado por LLMs"** — Qualidade de Software,
Departamento de Informática, Universidade Estadual de Maringá (UEM), 2026.

Autores: Daniel Arruda de Santana, Felipe Fidelis do Nascimento,
Gabriel Valentim de Oliveira Dacie, Luciano Trevisan Alberti.

## Questão de pesquisa

> Quais diferenças são observadas na quantidade e na densidade de ocorrências
> relacionadas à segurança entre código humano e código gerado por LLMs, quando
> submetidos às ferramentas de análise estática Semgrep e SonarQube?

## Desenho em uma tela

```
GitHub (top estrelas, Python)
   └─ 50 candidatos (critérios automáticos)  ── configuracao/repositorios_50_gitstars.yaml
        └─ 16 finalistas (leitura do README em pares) ── configuracao/repositorios_16_finalistas.yaml
             ├─ CH  código humano: último commit até 31/12/2020
             └─ README + docs + manifestos ── prompts/<slug>/prompt_recriacao.txt
                   ├─ GPT  (OpenAI)
                   ├─ CLD  (Anthropic)
                   └─ GEM  (Google)
   CH, GPT, CLD, GEM ──> Semgrep 1.176.1 (p/default) + SonarQube 26.9 (Sonar way, **/*.py)
                     ──> contagens absolutas e densidade por 1.000 linhas físicas (KLOC)
```

Uma geração por modelo e projeto. Os prompts não impõem regras de segurança
além das escritas em `prompt_recriacao.txt`. O código gerado é guardado sem
edição manual.

## O que está neste repositório

| Pasta | Conteúdo |
| --- | --- |
| `configuracao/` | Critérios, coleta bruta dos 100 candidatos (`github_top100_raw.json`), auditoria de inclusão/exclusão (`auditoria_selecao_gitstars.csv`), os 50 candidatos com SHA de corte e os 16 finalistas. Versões das ferramentas em `ferramentas.yaml`; modelos em `modelos.yaml`. |
| `prompts/<slug>/` | `prompt_recriacao.txt` (o prompt enviado às LLMs) e o README de referência no commit de corte. |
| `projetos/<slug>/{openai,gemini,claude}/` | Lugar do código gerado por cada LLM. |
| `dados_brutos/{semgrep,sonarqube}/<slug>/<origem>.json` | Saída original das ferramentas. **É a evidência do estudo**: todo número das tabelas sai daqui. |
| `resultados/resultados_scan_humano/<slug>/` | Relatório legível por repositório, análise do README, arquitetura textual e logs técnicos do scan. |
| `resultados/resultados_scan_IA/` | Tabela consolidada `tabela_final_humano_x_ia.{csv,xlsx}`. |
| `scripts/` | Seleção, restauração do código humano, scans e consolidação. |
| `pipeline_interno/` | Implementação do piloto (`anxolerd/dvpwa`, `bottlepy/bottle`) e da amostra anterior por tamanho, mantida para auditoria. |
| `docs/` | Diagrama da arquitetura do pipeline. |

### O que não é versionado, e por quê

- **Código humano** (`projetos/<slug>/humano/`): é reconstruído do GitHub pelo
  SHA registrado (cerca de 0,5 GB para os 50). Use
  `scripts/restaurar_codigo_humano.py`.
- **Ambientes virtuais, binário do SonarScanner, caches e clones de trabalho**:
  são reinstaláveis.
- **Credenciais**: nunca. Modelo em `pipeline_interno/secrets/providers.env.example`.

## Como reproduzir

Não é preciso chamar as LLMs para reproduzir a análise: o código gerado é a
entrada fixa. Gerar de novo tem custo e, como os modelos não são
determinísticos, produziria outro código.

### 1. Ambiente

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements/pipeline.txt
# só se for gerar código com as APIs:
.venv/bin/pip install -r requirements/provedores_ia.txt
```

Semgrep e SonarQube: versões congeladas e instalação em
`requirements/README.md` e `requirements/versoes_ferramentas.txt`.

### 2. Código humano de referência

```bash
.venv/bin/python scripts/restaurar_codigo_humano.py          # 16 finalistas
.venv/bin/python scripts/restaurar_codigo_humano.py --todos  # 50 candidatos
```

### 3. Análise estática (mesma configuração para as quatro origens)

```bash
semgrep scan --config p/default --metrics off --json projetos/<slug>/<origem> \
  > dados_brutos/semgrep/<slug>/<origem>.json

sonar-scanner -Dsonar.projectKey=<origem>-<slug> -Dsonar.sources=. \
  -Dsonar.inclusions='**/*.py' -Dsonar.python.version=3
```

O fluxo completo do scan humano, com a consulta à API do SonarQube, está em
`pipeline_interno/scan_repo_wsl.sh` e `scripts/processar_50_humanos.py`.

### 4. Consolidação

```bash
.venv/bin/python scripts/atualizar_resultados.py
.venv/bin/python scripts/gerar_relatorio_humano.py
```

Campo vazio na tabela significa "não executado", nunca zero. Os resultados do
Semgrep e do SonarQube não são somados, porque as duas ferramentas podem
apontar a mesma ocorrência.

## Métrica

Densidade = ocorrências ÷ linhas físicas dos arquivos `.py` analisados
(brancos e comentários incluídos) × 1.000. A mesma contagem vale para os
quatro grupos. A normalização reduz o efeito do tamanho, mas não corrige
diferenças de escopo funcional entre o projeto humano e a reconstrução.

## Seleção dos casos

Critérios automáticos (os 50 candidatos): linguagem principal Python; público,
não arquivado, sem ser fork; criado antes de 01/01/2021; commit até
31/12/2020 23:59:59 UTC; software executável; pelo menos 500 linhas Python não
vazias no commit de corte; ordem decrescente de estrelas.
`scripts/selecionar_50_repositorios.py` refaz a seleção. Com o limite anônimo da
API do GitHub, exporte `GITHUB_TOKEN`, sem gravá-lo em arquivo.

Exclusão na leitura em pares do README (50 → 16): documentação insuficiente;
escala grande demais para reconstrução por LLM; ML que exige treinamento
prévio; uso contrário às diretrizes éticas dos modelos.

As estrelas são um retrato da data registrada no YAML.

## Limitações

Uma única geração por modelo; o README como especificação; equivalência
funcional não demonstrada; falsos positivos e negativos da análise estática;
recorte de 16 projetos Python populares. Detalhes na seção 5 do artigo.
