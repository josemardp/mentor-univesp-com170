<#
.SYNOPSIS
  Abre o painel Mentor UNIVESP no navegador, garantindo que o servidor local esteja no ar.
#>
[CmdletBinding()]
param(
    [switch]$Atualizar
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$url = "http://127.0.0.1:8790/"

Push-Location $repo
try {
    if ($Atualizar) {
        Write-Host "Atualizando painel via coleta..." -ForegroundColor Yellow
        & python automacao\gerar_guia.py
    }

    # Verifica se o servidor local ja esta respondendo
    $servidorAtivo = $false
    try {
        $resp = Invoke-RestMethod -Uri "$url`__painel_info__" -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($resp.status -eq 'ok') { $servidorAtivo = $true }
    } catch {}

    if (-not $servidorAtivo) {
        # Inicia o servidor local seguro em segundo plano sem janela
        $servidorPy = Join-Path $repo "automacao\servidor.py"
        $docsDir    = Join-Path $repo "docs"

        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "conhost.exe"
        $psi.Arguments = "--headless python `"$servidorPy`" --porta 8790 --raiz `"$docsDir`""
        $psi.WorkingDirectory = $repo
        $psi.UseShellExecute = $true
        $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
        [System.Diagnostics.Process]::Start($psi) | Out-Null

        # Aguarda ate 3 segundos
        for ($i = 0; $i -lt 6; $i++) {
            Start-Sleep -Milliseconds 500
            try {
                $resp = Invoke-RestMethod -Uri "$url`__painel_info__" -TimeoutSec 1 -ErrorAction SilentlyContinue
                if ($resp.status -eq 'ok') {
                    $servidorAtivo = $true
                    break
                }
            } catch {}
        }
    }

    # Procura o executavel do Chrome
    $chromePaths = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
    )
    $chrome = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

    if ($chrome) {
        Start-Process $chrome $url
    } else {
        Start-Process $url
    }
} finally {
    Pop-Location
}
