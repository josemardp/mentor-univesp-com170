# -*- coding: utf-8 -*-
<#
.SYNOPSIS
  Configura ou valida o ambiente local do Mentor UNIVESP (tarefas agendadas e atalho na Area de Trabalho).
.DESCRIPTION
  Executado automaticamente pelo "Atualizar todos os projetos" ou manualmente.
  Idempotente: confere se as tarefas e o atalho ja existem antes de recriar.
  Nao exige elevacao de Administrador para registrar tarefas do proprio usuario.
#>

$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $PSScriptRoot
$ps1Rotina = Join-Path $repo "automacao\rodar_diario.ps1"
$ps1Abrir  = Join-Path $repo "automacao\abrir_painel.ps1"
$conhost   = "$env:SystemRoot\System32\conhost.exe"

# 1. Tarefas Agendadas no Windows
try {
    $tarefasExistentes = @(Get-ScheduledTask | Where-Object { $_.TaskName -like "Univesp - *" } | Select-Object -ExpandProperty TaskName)
    $precisaRegistrar = $false
    foreach ($nome in @("Univesp - guia diario", "Univesp - guia alerta", "Univesp - vigia")) {
        if ($tarefasExistentes -notcontains $nome) {
            $precisaRegistrar = $true
            break
        }
    }

    if ($precisaRegistrar) {
        $settings = New-ScheduledTaskSettingsSet `
            -StartWhenAvailable `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 40) `
            -MultipleInstances IgnoreNew

        function NovaAcao($modoArg) {
            $args = "--headless powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$ps1Rotina`""
            if ($modoArg) { $args += " -Modo $modoArg" }
            New-ScheduledTaskAction -Execute $conhost -Argument $args -WorkingDirectory $repo
        }

        # Diario (07:30)
        Unregister-ScheduledTask -TaskName "Univesp - guia diario" -Confirm:$false -ErrorAction SilentlyContinue
        Register-ScheduledTask `
            -TaskName "Univesp - guia diario" `
            -Action (NovaAcao $null) `
            -Trigger (New-ScheduledTaskTrigger -Daily -At "07:30") `
            -Settings $settings `
            -Description "Le o AVA, gera o painel e envia o resumo do dia." | Out-Null

        # Alerta (13:00)
        Unregister-ScheduledTask -TaskName "Univesp - guia alerta" -Confirm:$false -ErrorAction SilentlyContinue
        Register-ScheduledTask `
            -TaskName "Univesp - guia alerta" `
            -Action (NovaAcao "alerta") `
            -Trigger (New-ScheduledTaskTrigger -Daily -At "13:00") `
            -Settings $settings `
            -Description "Rele o AVA no meio do dia e avisa se apareceu prazo novo." | Out-Null

        # Vigia (20:00)
        Unregister-ScheduledTask -TaskName "Univesp - vigia" -Confirm:$false -ErrorAction SilentlyContinue
        Register-ScheduledTask `
            -TaskName "Univesp - vigia" `
            -Action (NovaAcao "vigia") `
            -Trigger (New-ScheduledTaskTrigger -Daily -At "20:00") `
            -Settings $settings `
            -Description "Nao le o AVA: confere se o painel local ainda e de hoje." | Out-Null

        Write-Host "  [Mentor UNIVESP] 3 tarefas registradas no Agendador do Windows (07:30, 13:00, 20:00)." -ForegroundColor Green
    } else {
        Write-Host "  [Mentor UNIVESP] Tarefas agendadas ja estao em dia no Windows." -ForegroundColor DarkGray
    }
} catch {
    Write-Host "  [Mentor UNIVESP] Aviso ao verificar tarefas agendadas: $($_.Exception.Message)" -ForegroundColor Yellow
}

# 2. Atalho na Area de Trabalho
try {
    $desktops = @(
        [Environment]::GetFolderPath("Desktop"),
        "C:\Users\$env:USERNAME\Desktop",
        "C:\Users\$env:USERNAME\OneDrive\Desktop"
    ) | Select-Object -Unique | Where-Object { $_ -and (Test-Path $_) }

    $chromePaths = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
    )
    $chrome = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

    $wsh = New-Object -ComObject WScript.Shell
    $criou = $false
    foreach ($d in $desktops) {
        $lnkPath = Join-Path $d "Mentor UNIVESP.lnk"
        if (-not (Test-Path -LiteralPath $lnkPath)) {
            $s = $wsh.CreateShortcut($lnkPath)
            $s.TargetPath = "powershell.exe"
            $s.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ps1Abrir`""
            $s.WorkingDirectory = $repo
            if ($chrome) { $s.IconLocation = "$chrome,0" }
            $s.Description = "Mentor UNIVESP - Painel Diario"
            $s.Save()
            $criou = $true
        }
    }
    if ($criou) {
        Write-Host "  [Mentor UNIVESP] Atalho do Chrome criado na Area de Trabalho." -ForegroundColor Green
    } else {
        Write-Host "  [Mentor UNIVESP] Atalho da Area de Trabalho ja existe." -ForegroundColor DarkGray
    }
} catch {
    Write-Host "  [Mentor UNIVESP] Aviso ao verificar atalhos: $($_.Exception.Message)" -ForegroundColor Yellow
}
