
# Pipeline de coleta de código Python pré-LLM

Este projeto automatiza a primeira parte do experimento:

1. clona repositórios Python;
2. encontra o commit mais recente anterior à data de corte;
3. faz checkout nesse snapshot histórico;
4. extrai funções Python;
5. coleta docstrings, trechos de README/docs e referências em testes;
6. cria uma especificação funcional sem usar o corpo da função humana;
7. gera um prompt padronizado;
8. exporta CSV/JSONL para a etapa de geração com LLMs.

## Por que o corpo humano não entra no prompt?

O campo `human_code` é guardado apenas como baseline para análise posterior.
O prompt é construído usando a assinatura e a docstring. O script também salva
contextos de README e testes para revisão.

Isso reduz o risco de a IA receber a implementação original e simplesmente
reproduzi-la.

## Pré-requisitos

- Python 3.11+
- Git instalado e disponível no PATH

Instalação:

```bash
pip install -r requirements.txt
```

## Configuração

Edite `config.yaml`.

Exemplo:

```yaml
cutoff_date: "2020-12-31"

repositories:
  - "TheAlgorithms/Python"
  - "bottlepy/bottle"
```

## Executar

Na pasta do projeto:

```bash
python collect.py
```

## Saídas

Serão criados:

```text
workspace/output/dataset_humano.csv
workspace/output/dataset_humano.jsonl
workspace/output/prompts.jsonl
```

Principais campos:

- `repo`
- `commit_sha`
- `commit_date`
- `file`
- `qualified_name`
- `signature`
- `docstring`
- `readme_context`
- `test_context`
- `human_code`
- `functional_spec`
- `prompt`

## Fluxo recomendado do experimento

```text
GitHub
  ↓
snapshot anterior ao corte
  ↓
funções humanas
  ↓
especificação funcional
  ↓
mesmo prompt
  ├── ChatGPT
  ├── Gemini
  └── Claude
  ↓
testes funcionais equivalentes
  ↓
Semgrep + SonarQube
  ↓
comparação
```

## Observação importante

Esta é uma automação de coleta e criação de prompts.

Para o trabalho acadêmico, recomenda-se revisar uma amostra dos prompts antes
de disparar a geração em massa. Isso serve para garantir que a docstring não
revele detalhes de implementação e que o requisito seja suficiente para uma
implementação funcional equivalente.

A próxima etapa pode automatizar:
- envio do mesmo prompt às três LLMs;
- salvamento das respostas por `sample_id`;
- execução dos testes;
- Semgrep;
- SonarQube;
- consolidação dos resultados em CSV.

## Etapa 2: geração e análise comparativa

As credenciais reais ficam em `secrets/providers.env` (ignorado pelo Git). O arquivo
`secrets/providers.env.example` é o modelo compartilhável, com campos vazios.

Antes de consumir APIs, confira a seleção sem custo:

```powershell
.\.venv\Scripts\python.exe generate.py --provider openai --limit 2 --dry-run
```

Para gerar implementações, informe sempre um provedor e um limite explícito:

```powershell
.\.venv\Scripts\python.exe generate.py --provider openai --limit 2
.\.venv\Scripts\python.exe generate.py --provider gemini --limit 2
.\.venv\Scripts\python.exe generate.py --provider claude --limit 2
```

Os códigos são gravados em `workspace/generated/<provider>/<sample_id>.py` e o
manifesto comum em `workspace/generated/generations.jsonl`. Execuções repetidas
pulam arquivos existentes, salvo quando `--overwrite` for informado.

Análise e consolidação:

```powershell
.\.venv\Scripts\python.exe analyze.py
.\.venv\Scripts\python.exe consolidate.py
```

O resultado final é `workspace/output/resultado_comparativo.csv`. A análise marca
os testes como `not_configured` até que uma estratégia reproduzível de injeção e
dependências seja definida para cada repositório; o texto encontrado próximo aos
testes pelo coletor não é executado como se fosse uma suíte completa.

Para entregar somente prompts a outra pessoa, sem chaves e sem `human_code`:

```powershell
.\.venv\Scripts\python.exe prepare_handoff.py --provider all
```

O pacote será criado em `workspace/handoff`.

Quando um colaborador devolver um arquivo JSONL, importe-o com:

```powershell
.\.venv\Scripts\python.exe import_generations.py caminho\respostas.jsonl
```

Cada linha deve conter `id`, `provider`, `model` e `generated_code`. O importador
valida IDs e provedores antes de gravar os arquivos no manifesto comum.

### SonarQube

Se o Docker Desktop estiver disponível, suba o servidor com:

```powershell
docker compose -f sonarqube/compose.yaml up -d
```

Depois configure um token do SonarQube fora do repositório e execute o
`sonar-scanner` usando `sonar-project.properties`. O servidor e o scanner não são
necessários para usar geração, sintaxe, Semgrep ou consolidação.
