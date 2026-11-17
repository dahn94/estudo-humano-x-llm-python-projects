# Estudo comparativo no nível de repositório

Este fluxo compara snapshots humanos anteriores a 2021 com projetos completos
gerados por modelos usando somente README, documentação e manifestos públicos.

## Preparação do Windows

O Semgrep não oferece funcionamento confiável no binário nativo desta máquina.
Abra PowerShell como administrador e execute:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\repository_study\habilitar_wsl_admin.ps1
```

Reinicie o Windows, instale o Ubuntu conforme a mensagem do script e, dentro dele,
execute `repository_study/setup_ubuntu.sh`. O script instala Semgrep, Java 21,
Docker Engine e Docker Compose. Assim, o SonarQube pode usar o Compose incluído.

## Desenho experimental

- `positive_controls`: aplicações deliberadamente vulneráveis, usadas para confirmar
  que as ferramentas detectam sinal de segurança.
- `real_world`: projetos reais, analisados separadamente para reduzir viés de seleção.
- Todos os grupos usam a mesma data de corte e a mesma configuração do Semgrep.
- Relatórios JSON brutos são preservados; o CSV é apenas uma visão agregada.
- Projetos sem tamanho mínimo ficam registrados no inventário, mas são excluídos.
- A inclusão não deve ser alterada depois de observar qual modelo “ganhou”.

## Preparação

```powershell
.\.venv\Scripts\python.exe repository_study\prepare_projects.py
```

O comando produz `inventory.jsonl` e `project_prompts.jsonl`. Os prompts não contêm
arquivos `.py` nem corpos de funções humanas.

O relatório de inclusão é gerado com:

```powershell
.\.venv\Scripts\python.exe repository_study\selection_report.py
```

Um projeto só recebe decisão `included` depois que o Semgrep oficial termina e
encontra ao menos uma ocorrência. Até lá, a decisão permanece `pending`. Isso
garante sinal mínimo sem esconder no inventário os candidatos excluídos.

## Geração

```powershell
.\.venv\Scripts\python.exe repository_study\generate_projects.py --provider openai --limit 1 --dry-run
.\.venv\Scripts\python.exe repository_study\generate_projects.py --provider openai --limit 1
```

Cada resposta deve ser um projeto multifile em JSON. Caminhos absolutos e `..` são
recusados antes da gravação.

## Semgrep

Política oficial configurada: `p/default` do Semgrep Registry.

```powershell
.\.venv\Scripts\python.exe repository_study\scan_projects.py --origin human
```

Se o Registry não estiver acessível, `--local-rules` permite diagnóstico, mas esses
resultados não devem ser misturados com `p/default` na tabela acadêmica.

## SonarQube

Após instalar Docker Desktop:

```powershell
docker compose -f repository_study\sonarqube\compose.yaml up -d
```

O mesmo servidor, Quality Profile e versão do scanner devem ser congelados para
humanos e modelos. Guarde o token em `secrets/providers.env` como `SONAR_TOKEN`.

Execute e colete as métricas com:

```powershell
.\.venv\Scripts\python.exe repository_study\run_sonarqube.py --origin human
```

## Consolidação

```powershell
.\.venv\Scripts\python.exe repository_study\consolidate.py
```

Saída: `workspace/repository_study/resultado_comparativo_projetos.csv`.
