<#
Rodada diaria do guia, na maquina do aluno.

Este script existe porque em 11/09/2026 o GitHub Pages foi desligado e os dois
workflows agendados sairam junto (eles publicavam o painel, e o painel carrega
nome completo de colega). O codigo continuou funcionando, mas parou de rodar
sozinho: o robo passou a depender de o Josemar lembrar de digitar o comando. Em
15/09/2026 isso custou um prazo que so apareceu porque alguem abriu o painel a
mao. O agendamento voltou, agora local, e este arquivo e o que a tarefa do
Windows dispara.

  .\rodar_diario.ps1              rodada da manha: le o AVA e manda o resumo
  .\rodar_diario.ps1 -Modo alerta rodada do meio do dia: so fala se apareceu
                                  prazo novo e perto
  .\rodar_diario.ps1 -SemColeta   so refaz o painel com o que ja foi lido
  .\rodar_diario.ps1 -Modo vigia  nao le o AVA: so confere se o painel local
                                  ainda e de hoje, e reclama se nao for

Canais de aviso, nesta ordem:
  1. e-mail, se as variaveis SMTP_* estiverem no ambiente (o canal original);
  2. notificacao do Windows, sempre que houver acao para hoje ou amanha.
O segundo existe porque um agendador que roda em silencio nao resolve o
problema que ele foi criado para resolver.

As tarefas chamam este script por "conhost.exe --headless powershell.exe ...",
e nao por powershell.exe direto. No Windows 11 com o Windows Terminal como
console padrao, "-WindowStyle Hidden" e ignorado e cada rodada abria uma aba
do Terminal na frente do que o Josemar estivesse fazendo (15/09/2026). O
conhost sem janela resolve sem trocar o console padrao da maquina.
#>
[CmdletBinding()]
param(
    [ValidateSet('diario', 'alerta', 'vigia')]
    [string]$Modo = 'diario',
    [switch]$SemColeta
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$env:PYTHONUTF8 = '1'
# Sob conhost --headless o console nasce em cp850, e o UTF-8 do Python chega
# ao log como "├®". Sob o Windows Terminal nao acontecia, porque ele ja abre
# em UTF-8; e por isso que o defeito so apareceu depois da troca.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
# Sem isto, falta de SMTP derruba a rodada inteira e o painel nao e gerado. O
# painel local vale por si: o e-mail e um canal, nao o produto.
$env:EMAIL_OPCIONAL = '1'

$logDir = Join-Path $repo 'tmp\log'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$log = Join-Path $logDir 'rodar_diario.log'

# Write-Host, e nao Write-Output: o que vai para o pipeline vira valor de
# retorno da funcao que chamou, e "Invoca" passaria a devolver um array em vez
# do codigo de saida. Foi o que fez a primeira rodada de teste acusar falha num
# render que tinha terminado com 0.
function Escreve($texto) {
    $linha = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $texto
    Add-Content -Path $log -Value $linha -Encoding UTF8
    Write-Host $linha
}

function Invoca($titulo, $argumentos) {
    Escreve "-> $titulo"
    # Python escreve aviso em stderr e isso nao e erro; com 'Stop' o 2>&1
    # derrubaria a funcao antes de ler o codigo de saida.
    $ErrorActionPreference = 'Continue'
    $saida = & python @argumentos 2>&1
    $codigo = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    foreach ($linha in $saida) { Add-Content -Path $log -Value "    $linha" -Encoding UTF8 }
    Escreve "<- $titulo terminou com codigo $codigo"
    return [int]$codigo
}

# Notificacao do Windows. Vale so em sessao interativa, que e o caso: a tarefa
# roda como o usuario logado, com a janela oculta. Balloon do NotifyIcon em vez
# de modulo externo, para nao criar dependencia de instalacao.
function Avisa($titulo, $texto) {
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $icone = New-Object System.Windows.Forms.NotifyIcon
        $icone.Icon = [System.Drawing.SystemIcons]::Information
        $icone.BalloonTipTitle = $titulo
        $icone.BalloonTipText = $texto
        $icone.Visible = $true
        $icone.ShowBalloonTip(20000)
        Start-Sleep -Seconds 12
        $icone.Dispose()
        Escreve "Notificacao mostrada: $titulo"
    } catch {
        Escreve "Nao consegui notificar na tela: $($_.Exception.Message)"
    }
}

# O que vence hoje ou amanha, lido do painel recem-gerado. O painel e a fonte:
# repetir aqui a regra de urgencia seria uma segunda versao dela para divergir
# da primeira.
function ResumoUrgente {
    $py = @'
import json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
BR = timezone(timedelta(hours=-3))
p = Path(sys.argv[1]) / "docs" / "data.json"
if not p.exists():
    sys.exit(0)
d = json.loads(p.read_text(encoding="utf-8"))
hoje = datetime.now(BR).date()
urgentes = []
for a in d.get("acoes") or []:
    if a.get("urgencia") in ("hoje", "amanha"):
        urgentes.append("{}: {}".format(a.get("curso", "?"), (a.get("o_que") or "")[:70]))
if urgentes:
    print("\n".join(urgentes[:5]))
'@
    $arquivo = Join-Path $env:TEMP 'univesp_urgente.py'
    Set-Content -Path $arquivo -Value $py -Encoding UTF8
    $texto = & python $arquivo $repo 2>&1
    Remove-Item $arquivo -Force -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -ne 0) { return $null }
    return ($texto -join "`n").Trim()
}

Push-Location $repo
try {
    Escreve "=== rodada '$Modo' comecou ==="

    if ($Modo -eq 'vigia') {
        # O vigia e a unica coisa que pega a rodada que NAO aconteceu, por isso
        # fica fora dela: se morasse dentro do diario, sumiria junto com ele.
        # Exit 0 e painel em dia, e o vigia nao fala nada; vigia que fala todo
        # dia deixa de ser lido.
        $codigo = Invoca 'vigia' @('automacao/vigia.py')
        if ($codigo -ne 0) {
            Invoca 'vigia --avisar' @('automacao/vigia.py', '--avisar') | Out-Null
            Avisa 'Univesp: o guia parou de atualizar' 'A rodada de hoje nao aconteceu. Veja tmp\log\rodar_diario.log.'
            Escreve '=== vigia: guia CONGELADO ==='
            exit 1
        }
        Escreve '=== vigia: guia em dia ==='
        exit 0
    }

    $falhou = $null
    if (-not $SemColeta) {
        if ((Invoca 'gerar_guia' @('automacao/gerar_guia.py')) -ne 0) { $falhou = 'gerar_guia' }
    } else {
        if ((Invoca 'render' @('automacao/gerar_guia.py', '--render-only')) -ne 0) { $falhou = 'render' }
    }

    if ($falhou) {
        # Rodada que morre calada e o defeito que o vigia existe para pegar.
        # Aqui da para avisar na hora, sem esperar o vigia do dia seguinte.
        $env:PASSO_FALHOU = $falhou
        Invoca 'aviso de falha' @('automacao/enviar_email.py', '--falha') | Out-Null
        Avisa 'Univesp: o robo nao terminou' "Falhou em $falhou. Veja tmp\log\rodar_diario.log."
        Escreve "=== rodada terminou COM FALHA em $falhou ==="
        exit 1
    }

    $argsEmail = @('automacao/enviar_email.py')
    if ($Modo -eq 'alerta') { $argsEmail += '--alerta' }
    Invoca "e-mail ($Modo)" $argsEmail | Out-Null

    $urgente = ResumoUrgente
    if ($urgente) {
        Avisa 'Univesp: vence hoje ou amanha' $urgente
    } else {
        Escreve 'Nada para hoje ou amanha; nao notifico na tela.'
    }

    Escreve '=== rodada terminou ==='
    exit 0
} finally {
    Pop-Location
}
