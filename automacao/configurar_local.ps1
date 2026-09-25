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
    # Destravar: tambem dispara no logon e no desbloqueio da tela, porque o
    # horario fixo perdido em suspensao nao e recuperado (22/09/2026). O vigia
    # fica so no horario: ele e quem denuncia a falha, e no desbloqueio da
    # manha acusaria painel velho antes de a rodada do dia acontecer.
    @{ Nome = "Univesp - guia diario"; Modo = $null; Hora = "07:30"; Minutos = 60; Destravar = $true
       Descricao = "Le o AVA, gera o painel e envia o resumo do dia." },
    @{ Nome = "Univesp - guia alerta"; Modo = "alerta"; Hora = "13:00"; Minutos = 60; Destravar = $true
       Descricao = "Rele o AVA no meio do dia e avisa se apareceu prazo novo." },
    @{ Nome = "Univesp - vigia"; Modo = "vigia"; Hora = "20:00"; Minutos = 5
       Descricao = "Nao le o AVA: confere se o painel local ainda e de hoje." },
    # Trabalho semanal, gatilho diario: a guarda do rodar_diario.ps1 sai quieta
    # se a semana ja foi feita, e o disparo das 10:00 de terca em diante
    # recupera a segunda perdida sem depender de desbloqueio da tela
    # (pendencia da auditoria do Codex, 23/09/2026). 180 minutos porque chama
    # o Claude por disciplina (4 min por semana, medido em 22/09/2026).
    @{ Nome = "Univesp - revisao semanal"; Modo = "revisao"; Hora = "10:00"; Minutos = 180
       Destravar = $true
       Descricao = "Segunda: junta o material da semana que terminou e monta a revisao de prova em privado\estudo." }
)

function ArgumentosDe($modoArg) {
    $texto = "--headless powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$ps1Rotina`""
    if ($modoArg) { $texto += " -Modo $modoArg" }
    # -Agendada liga a guarda de "ja feita" do rodar_diario.ps1 (gatilhos de
    # logon e desbloqueio); rodada digitada a mao nao passa e roda sempre.
    $texto += " -Agendada"
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
        } elseif ($alvo.Dia -and @($atual.Triggers | Where-Object { $_.DaysOfWeek -eq 2 }).Count -eq 0) {
            # DaysOfWeek e mascara de bits: domingo 1, segunda 2.
            $motivo = "nao estava so na segunda-feira"
        } elseif (-not $alvo.Dia -and @($atual.Triggers | Where-Object {
                    $_.CimClass.CimClassName -eq 'MSFT_TaskWeeklyTrigger' }).Count -gt 0) {
            $motivo = "era semanal, agora e diaria com guarda"
        } elseif ($alvo.Destravar -and @($atual.Triggers | Where-Object {
                    $_.CimClass.CimClassName -eq 'MSFT_TaskSessionStateChangeTrigger' }).Count -eq 0) {
            $motivo = "nao tinha o gatilho de desbloqueio da tela"
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

        $gatilho = @(if ($alvo.Dia) {
            New-ScheduledTaskTrigger -Weekly -DaysOfWeek $alvo.Dia -At $alvo.Hora
        } else {
            New-ScheduledTaskTrigger -Daily -At $alvo.Hora
        })
        if ($alvo.Destravar) {
            # Logon e desbloqueio: o horario fixo nao e recuperado quando o
            # notebook passa a manha suspenso (22/09/2026). O proprio
            # rodar_diario.ps1 decide se ainda ha o que fazer.
            $usuario = "$env:USERDOMAIN\$env:USERNAME"
            $gatilho += New-ScheduledTaskTrigger -AtLogOn -User $usuario
            $classe = Get-CimClass -Namespace 'Root/Microsoft/Windows/TaskScheduler' -ClassName 'MSFT_TaskSessionStateChangeTrigger'
            $desbloqueio = New-CimInstance -CimClass $classe -ClientOnly
            $desbloqueio.StateChange = 8   # TASK_SESSION_UNLOCK
            $desbloqueio.UserId = $usuario
            $desbloqueio.Enabled = $true
            $gatilho += $desbloqueio
        }
        Unregister-ScheduledTask -TaskName $alvo.Nome -Confirm:$false -ErrorAction SilentlyContinue
        Register-ScheduledTask `
            -TaskName $alvo.Nome `
            -Action (New-ScheduledTaskAction -Execute $conhost -Argument $argumentos -WorkingDirectory $repo) `
            -Trigger $gatilho `
            -Settings $settings `
            -Description $alvo.Descricao | Out-Null
        $refeitas += "$($alvo.Nome): $motivo"
    }

    if ($refeitas.Count -gt 0) {
        Write-Host "  [Mentor UNIVESP] Tarefas ajustadas no Agendador do Windows:" -ForegroundColor Green
        foreach ($linha in $refeitas) { Write-Host "    - $linha" -ForegroundColor Green }
    } else {
        Write-Host "  [Mentor UNIVESP] 4 tarefas agendadas conferidas por dentro e em dia (07:30, 13:00, 20:00 e revisao 10:00)." -ForegroundColor DarkGray
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

# 3. Atalho privado/ para o acervo no Google Drive
#
# O repositorio e publico (vitrine do LinkedIn). Coleta do AVA, gabarito e a
# prova diagnostica da formacao complementar ficam no Drive, que tem o mesmo
# caminho nas duas maquinas; so a letra da unidade pode mudar. A pasta
# privado/ esta no .gitignore.
try {
    $relPrivado = "Meu Drive\10_JOSEMAR_PESSOAL\02_PROJETOS_ATIVOS\02_TECNOLOGIA_E_IA\mentor-univesp-privado"
    $alvoPrivado = Get-PSDrive -PSProvider FileSystem |
        ForEach-Object { Join-Path $_.Root $relPrivado } |
        Where-Object { Test-Path -LiteralPath $_ } |
        Select-Object -First 1
    $linkPrivado = Join-Path $repo "privado"

    if (-not $alvoPrivado) {
        Write-Host "  [Mentor UNIVESP] Google Drive nao montado: privado/ nao foi criado." -ForegroundColor Yellow
    } elseif ((Get-Item -LiteralPath $linkPrivado -Force -ErrorAction SilentlyContinue).LinkType -eq 'Junction' -and
              (Get-Item -LiteralPath $linkPrivado -Force).Target -ne $alvoPrivado) {
        # A pasta do Drive mudou de lugar (renumeracao de 25/09/2026): refaz o atalho.
        # Apagar uma junction remove so o atalho, nunca o conteudo do Drive.
        [IO.Directory]::Delete($linkPrivado)
        New-Item -ItemType Junction -Path $linkPrivado -Target $alvoPrivado | Out-Null
        Write-Host "  [Mentor UNIVESP] privado/ refeito, apontando para $alvoPrivado" -ForegroundColor Green
    } elseif (Test-Path -LiteralPath $linkPrivado) {
        Write-Host "  [Mentor UNIVESP] privado/ ja existe." -ForegroundColor DarkGray
    } else {
        New-Item -ItemType Junction -Path $linkPrivado -Target $alvoPrivado | Out-Null
        Write-Host "  [Mentor UNIVESP] privado/ criado, apontando para $alvoPrivado" -ForegroundColor Green
    }
} catch {
    Write-Host "  [Mentor UNIVESP] Aviso ao criar privado/: $($_.Exception.Message)" -ForegroundColor Yellow
}
