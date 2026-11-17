# Dependencias para executar o pipeline

Esta pasta centraliza as dependencias do estudo. As dependencias dos 50 projetos analisados nao devem ser instaladas para executar os scans estaticos; elas pertencem a cada projeto e podem ser inseguras ou incompatíveis por serem versoes antigas.

## 1. Requisitos do computador

- Windows 10 ou 11;
- Git;
- Python 3.11 ou 3.12;
- WSL 2 com Ubuntu;
- Docker instalado dentro do Ubuntu/WSL;
- pelo menos 16 GB de RAM recomendados;
- espaco livre suficiente para os snapshots e resultados.

O SonarQube e o Semgrep devem ser executados no Ubuntu/WSL. O pacote Python principal pode ser executado no Windows.

## 2. Ambiente Python do pipeline

Abra o PowerShell na raiz de `python_prellm_pipeline` e execute:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r .\requirements\pipeline.txt
```

Para também chamar OpenAI, Gemini e Claude:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements\provedores_ia.txt
```

Para instalar tudo de uma vez:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements\completo.txt
```

As chaves de API devem ser configuradas como variaveis de ambiente. Nunca grave credenciais nos arquivos do projeto.

## 3. Semgrep no Ubuntu/WSL

Abra o Ubuntu e execute:

```bash
sudo apt update
sudo apt install -y python3 python3-pip pipx git curl
pipx ensurepath
pipx install "semgrep==1.176.1"
semgrep --version
```

Feche e abra o Ubuntu novamente se o comando `semgrep` ainda nao estiver no `PATH`.

O estudo deve usar a mesma configuracao de regras para projetos humanos e projetos gerados por IA. Se `p/default` estiver inacessivel pela rede, registre a limitacao e use o arquivo versionado `pipeline_interno/semgrep-rules.yaml` em todos os grupos.

## 4. SonarQube no Ubuntu/WSL

Com Docker funcionando dentro do Ubuntu:

```bash
docker run -d --name sonarqube-sonarqube-1 \
  --restart unless-stopped \
  -p 9000:9000 \
  sonarqube:community
```

Abra `http://localhost:9000`, conclua a configuracao inicial e crie um token. O arquivo local esperado pelo executor e:

```text
pipeline_interno/secrets/sonar.env
```

Conteudo:

```text
SONAR_TOKEN=COLOQUE_O_TOKEN_AQUI
```

Esse arquivo contem segredo e nao deve ser compartilhado. Cada integrante deve criar o proprio token.

O SonarScanner utilizado pelo projeto fica em `pipeline_interno/tools/sonar-scanner`. A versao metodologica esta registrada em `configuracao/ferramentas.yaml`.

## 5. Validacao

Na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -c "import yaml, requests, dotenv; print('Dependencias Python: OK')"
wsl.exe -d Ubuntu -- bash -lc "semgrep --version && docker --version"
```

Depois execute o pipeline conforme o `README.md` da raiz. Erros e saidas de diagnostico ficam nas pastas `logs_tecnicos`; os resultados cientificos ficam nos relatorios e JSONs brutos.

