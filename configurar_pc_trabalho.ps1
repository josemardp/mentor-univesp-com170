# -*- coding: utf-8 -*-
<#
.SYNOPSIS
  Configura a automacao e o painel do Mentor UNIVESP no PC do trabalho.
.DESCRIPTION
  1. Atualiza o repositorio local (git pull) ou clona caso nao exista.
  2. Instala dependencias Python (requirements.txt + playwright).
  3. Registra as 3 tarefas no Agendador do Windows (07:30, 13:00, 20:00) em modo headless.
  4. Cria o atalho do Chrome "Mentor UNIVESP" na Area de Trabalho do usuario.
  5. Valida o ambiente.
.NOTES
  Execute no PowerShell como Administrador para registrar as tarefas agendadas.
#>

[CmdletBinding()]
param(
    [string]$Destino = "C:\projetos\mentor-univesp"
)

$ErrorActionPreference = 'Stop'

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  Mentor UNIVESP - Configuracao do PC do Trabalho     " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verifica privilegios de Administrador
$ehAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $ehAdmin) {
    Write-Host "[AVISO] Para registrar tarefas no Agendador do Windows, este script precisa rodar como Administrador." -ForegroundColor Yellow
    Write-Host "Reabrindo como Administrador..." -ForegroundColor Yellow
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 0
}

# 2. Garante diretorio do projeto
if (-not (Test-Path $Destino)) {
    Write-Host "-> Clonando repositorio em $Destino..." -ForegroundColor Yellow
    $parent = Split-Path $Destino -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    git clone https://github.com/josemardp/mentor-univesp-com170.git $Destino
} else {
    Write-Host "-> Atualizando repositorio via git pull..." -ForegroundColor Yellow
    Push-Location $Destino
    try {
        git pull --ff-only
    } catch {
        Write-Host "   (aviso: git pull falhou ou requer merge manual, mantendo versao local)" -ForegroundColor DarkYellow
    } finally {
        Pop-Location
    }
}

Push-Location $Destino
try {
    # 3. Dependencias Python
    Write-Host "-> Verificando dependencias Python..." -ForegroundColor Yellow
    if (Test-Path "automacao\requirements.txt") {
        python -m pip install --upgrade -r automacao\requirements.txt --quiet
    }
    python -m playwright install chromium

    # 4. Registra tarefas agendadas no Windows
    Write-Host "-> Registrando tarefas agendadas no Windows..." -ForegroundColor Yellow
    $ps1     = Join-Path $Destino "automacao\rodar_diario.ps1"
    $conhost = "$env:SystemRoot\System32\conhost.exe"
    $usuario = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 40) `
        -MultipleInstances IgnoreNew

    $principal = New-ScheduledTaskPrincipal `
        -UserId $usuario `
        -LogonType Interactive `
        -RunLevel Highest

    function NovaAcao($modoArg) {
        $args = "--headless powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$ps1`""
        if ($modoArg) { $args += " -Modo $modoArg" }
        New-ScheduledTaskAction -Execute $conhost -Argument $args -WorkingDirectory $Destino
    }

    # Tarefa 1: Diario (07:30)
    Unregister-ScheduledTask -TaskName "Univesp - guia diario" -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask `
        -TaskName "Univesp - guia diario" `
        -Action (NovaAcao $null) `
        -Trigger (New-ScheduledTaskTrigger -Daily -At "07:30") `
        -Settings $settings `
        -Principal $principal `
        -Description "Le o AVA, gera o painel e envia o resumo do dia." | Out-Null
    Write-Host "   [OK] Tarefa 'Univesp - guia diario' registrada (07:30)" -ForegroundColor Green

    # Tarefa 2: Alerta (13:00)
    Unregister-ScheduledTask -TaskName "Univesp - guia alerta" -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask `
        -TaskName "Univesp - guia alerta" `
        -Action (NovaAcao "alerta") `
        -Trigger (New-ScheduledTaskTrigger -Daily -At "13:00") `
        -Settings $settings `
        -Principal $principal `
        -Description "Rele o AVA no meio do dia e avisa se apareceu prazo novo." | Out-Null
    Write-Host "   [OK] Tarefa 'Univesp - guia alerta' registrada (13:00)" -ForegroundColor Green

    # Tarefa 3: Vigia (20:00)
    Unregister-ScheduledTask -TaskName "Univesp - vigia" -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask `
        -TaskName "Univesp - vigia" `
        -Action (NovaAcao "vigia") `
        -Trigger (New-ScheduledTaskTrigger -Daily -At "20:00") `
        -Settings $settings `
        -Principal $principal `
        -Description "Nao le o AVA: confere se o painel local ainda e de hoje." | Out-Null
    Write-Host "   [OK] Tarefa 'Univesp - vigia' registrada (20:00)" -ForegroundColor Green

    # 5. Atalho do Chrome na Area de Trabalho
    Write-Host "-> Criando atalho na Area de Trabalho..." -ForegroundColor Yellow
    $desktops = @(
        [Environment]::GetFolderPath("Desktop"),
        "C:\Users\$env:USERNAME\Desktop",
        "C:\Users\$env:USERNAME\OneDrive\Desktop"
    ) | Select-Object -Unique | Where-Object { Test-Path $_ }

    $chromePaths = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
    )
    $chrome = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

    $abrirScript = Join-Path $Destino "automacao\abrir_painel.ps1"
    $wsh = New-Object -ComObject WScript.Shell

    foreach ($d in $desktops) {
        $lnk = Join-Path $d "Mentor UNIVESP.lnk"
        $s = $wsh.CreateShortcut($lnk)
        $s.TargetPath = "powershell.exe"
        $s.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$abrirScript`""
        $s.WorkingDirectory = $Destino
        if ($chrome) { $s.IconLocation = "$chrome,0" }
        $s.Description = "Mentor UNIVESP - Painel Diario"
        $s.Save()
        Write-Host "   [OK] Atalho criado em: $lnk" -ForegroundColor Green
    }

    # 6. Aviso sobre credenciais
    Write-Host ""
    Write-Host "-> Verificacao de credenciais do AVA:" -ForegroundColor Yellow
    $storageState = Join-Path $Destino "automacao\storage_state.json"
    if (Test-Path $storageState) {
        Write-Host "   [OK] Sessao salva encontrada em storage_state.json." -ForegroundColor Green
    } elseif ($env:AVA_USUARIO -and $env:AVA_SENHA) {
        Write-Host "   [OK] Variaveis AVA_USUARIO e AVA_SENHA detectadas no ambiente." -ForegroundColor Green
    } else {
        Write-Host "   [ATENCAO] Esta maquina ainda nao possui login salvo nem variaveis AVA_USUARIO/AVA_SENHA." -ForegroundColor Yellow
        Write-Host "   Para a primeira coleta, execute: python automacao\gerar_guia.py" -ForegroundColor Yellow
        Write-Host "   (ou defina as variaveis de ambiente de usuario AVA_USUARIO e AVA_SENHA)." -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "======================================================" -ForegroundColor Green
    Write-Host "  Configuracao concluida com sucesso!                " -ForegroundColor Green
    Write-Host "======================================================" -ForegroundColor Green
} finally {
    Pop-Location
}
