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
#
# Conferir so o nome nao basta, e foi isso que deixou o defeito de 19/09/2026
# passar batido: as tres tarefas existiam, o atualizador dizia "ja estao em
# dia" e ninguem via o que tinha dentro delas. A definicao que vale mora na
# tabela abaixo, e a tarefa e refeita sempre que a maquina discordar dela.
#
# O limite de tempo das duas coletas subiu de 40 para 60 minutos: rodada em
# rede lenta ja tinha levado 29 minutos em 15/09, e 40 era pouca folga para
# uma leitura que varre mais de 60 foruns.
$desejado = @(
    @{ Nome = "Univesp - guia diario"; Modo = $null; Hora = "07:30"; Minutos = 60
       Descricao = "Le o AVA, gera o painel e envia o resumo do dia." },
    @{ Nome = "Univesp - guia alerta"; Modo = "alerta"; Hora = "13:00"; Minutos = 60
       Descricao = "Rele o AVA no meio do dia e avisa se apareceu prazo novo." },
    @{ Nome = "Univesp - vigia"; Modo = "vigia"; Hora = "20:00"; Minutos = 5
       Descricao = "Nao le o AVA: confere se o painel local ainda e de hoje." }
)

function ArgumentosDe($modoArg) {
    $texto = "--headless powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$ps1Rotina`""
    if ($modoArg) { $texto += " -Modo $modoArg" }
    return $texto
}

# Duracao gravada pelo Agendador, em TimeSpan. Comparar o texto nao serve: o
# Windows normaliza o que recebe, e "PT60M" volta escrito "PT1H". Com
# comparacao de texto o configurador achava diferenca em toda passada e
# refazia as tres tarefas para sempre.
function LimiteEmMinutos($texto) {
    if (-not $texto) { return -1 }
    try { return [int][System.Xml.XmlConvert]::ToTimeSpan($texto).TotalMinutes }
    catch { return -1 }
}

try {
    $refeitas = @()
    foreach ($alvo in $desejado) {
        $argumentos = ArgumentosDe $alvo.Modo
        $atual = Get-ScheduledTask -TaskName $alvo.Nome -ErrorAction SilentlyContinue

        $motivo = $null
        if (-not $atual) {
            $motivo = "nao existia"
        } elseif (@($atual.Actions).Count -ne 1 -or
                  (Split-Path -Leaf @($atual.Actions)[0].Execute) -ne (Split-Path -Leaf $conhost)) {
            # Pelo nome do arquivo, nao pelo caminho inteiro: tarefa antiga foi
            # gravada com "conhost.exe" pelado e caminho completo nao bate com
            # ela, o que fazia o configurador refazer as tres sem necessidade.
            $motivo = "chamava outro programa"
        } elseif (@($atual.Actions)[0].Arguments -ne $argumentos) {
            $motivo = "apontava para outro caminho ou outro modo"
        } elseif ((LimiteEmMinutos $atual.Settings.ExecutionTimeLimit) -ne $alvo.Minutos) {
            $motivo = "tinha limite de $($atual.Settings.ExecutionTimeLimit), devia ser $($alvo.Minutos) min"
        } elseif (-not $atual.Settings.StartWhenAvailable) {
            # Sem isto, rodada que cai com a maquina desligada some de vez, em
            # vez de acontecer quando ela liga.
            $motivo = "nao recuperava a rodada perdida com a maquina desligada"
        } elseif ($atual.Settings.DisallowStartIfOnBatteries) {
            $motivo = "nao rodava fora da tomada"
        } elseif ($atual.Settings.StopIfGoingOnBatteries) {
            $motivo = "morria no meio se o notebook saisse da tomada"
        } elseif (@($atual.Triggers | Where-Object { $_.StartBoundary -like "*T$($alvo.Hora):00*" }).Count -eq 0) {
            $motivo = "estava agendada em outro horario"
        }

        if (-not $motivo) { continue }

        # "-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries" nao e detalhe:
        # e o defeito achado em 19/09/2026 no PC do trabalho, que e notebook.
        # O padrao do New-ScheduledTaskSettingsSet e o contrario dos dois, e
        # com eles ligados o Windows simplesmente nao roda a tarefa fora da
        # tomada (ela fica em "Queued", sem erro nenhum para ninguem ver) e
        # ainda mata a que ja estava rodando se a pessoa tira o notebook da
        # tomada no meio. Tarefa que nao roda calada e o pior tipo de defeito
        # que este projeto ja teve, e este estava ali desde 15/09.
        $settings = New-ScheduledTaskSettingsSet `
            -StartWhenAvailable `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit (New-TimeSpan -Minutes $alvo.Minutos) `
            -MultipleInstances IgnoreNew

        Unregister-ScheduledTask -TaskName $alvo.Nome -Confirm:$false -ErrorAction SilentlyContinue
        Register-ScheduledTask `
            -TaskName $alvo.Nome `
            -Action (New-ScheduledTaskAction -Execute $conhost -Argument $argumentos -WorkingDirectory $repo) `
            -Trigger (New-ScheduledTaskTrigger -Daily -At $alvo.Hora) `
            -Settings $settings `
            -Description $alvo.Descricao | Out-Null
        $refeitas += "$($alvo.Nome): $motivo"
    }

    if ($refeitas.Count -gt 0) {
        Write-Host "  [Mentor UNIVESP] Tarefas ajustadas no Agendador do Windows:" -ForegroundColor Green
        foreach ($linha in $refeitas) { Write-Host "    - $linha" -ForegroundColor Green }
    } else {
        Write-Host "  [Mentor UNIVESP] 3 tarefas agendadas conferidas por dentro e em dia (07:30, 13:00, 20:00)." -ForegroundColor DarkGray
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
