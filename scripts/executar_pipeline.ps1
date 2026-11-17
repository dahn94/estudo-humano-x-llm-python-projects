param(
    [switch]$AtualizarPlanilha
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackageRoot = Split-Path -Parent $ScriptRoot
$Python = Join-Path $PackageRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python virtualenv não encontrado em $Python. Consulte o README.md da raiz."
}

& $Python (Join-Path $ScriptRoot "atualizar_resultados.py")
& $Python (Join-Path $ScriptRoot "gerar_relatorio_humano.py")

if ($AtualizarPlanilha) {
    $NodeCommand = Get-Command node -ErrorAction SilentlyContinue
    $Node = if ($NodeCommand) {
        $NodeCommand.Source
    } else {
        Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    }
    if (Test-Path -LiteralPath $Node) {
        & $Node (Join-Path $ScriptRoot "build_comparison_workbook.mjs")
    } else {
        Write-Warning "Runtime de planilhas não encontrado. O CSV foi atualizado normalmente."
    }
}

Write-Host "Pacote validado e tabela comparativa atualizada."
Write-Host "Campos sem execução permanecem vazios; não representam zero achado."
