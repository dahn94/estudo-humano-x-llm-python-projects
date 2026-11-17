# Execute este arquivo no PowerShell usando "Executar como administrador".
$ErrorActionPreference = "Stop"

Write-Host "Habilitando Subsistema do Windows para Linux..."
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

Write-Host "Habilitando Plataforma de Máquina Virtual..."
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

Write-Host "Recursos habilitados. Reinicie o Windows e execute:" -ForegroundColor Green
Write-Host "  wsl --install -d Ubuntu"
Write-Host "Depois, dentro do Ubuntu, execute repository_study/setup_ubuntu.sh."

