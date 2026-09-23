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
  .\rodar_diario.ps1 -Modo revisao segunda-feira: monta a revisao de prova da
                                  semana que terminou (automacao\revisao_semanal.py)

Canais de aviso, nesta ordem:
  1. e-mail, se as variaveis SMTP_* estiverem no ambiente (o canal original);
  2. notificacao do Windows, sempre que houver acao para hoje ou amanha.
O segundo existe porque um agendador que roda em silencio nao resolve o
problema que ele foi criado para resolver.

Uma coleta por vez, garantida por trava de arquivo em tmp\log\rodada.lock.
Rodada que chega e encontra a trava tomada sai com 0 e diz isso no log: o AVA
so aguenta uma sessao de cada vez, e duas leituras juntas derrubam as duas.

As tarefas chamam este script por "conhost.exe --headless powershell.exe ...",
e nao por powershell.exe direto. No Windows 11 com o Windows Terminal como
console padrao, "-WindowStyle Hidden" e ignorado e cada rodada abria uma aba
do Terminal na frente do que o Josemar estivesse fazendo (15/09/2026). O
conhost sem janela resolve sem trocar o console padrao da maquina.
#>
[CmdletBinding()]
param(
    [ValidateSet('diario', 'alerta', 'vigia', 'revisao')]
    [string]$Modo = 'diario',
    [switch]$SemColeta,
    # Posto pelas tarefas do Agendador. Liga a guarda de "ja feita hoje", que
    # existe por causa dos gatilhos de logon e desbloqueio. Rodada digitada a
    # mao nao passa este switch e roda sempre.
    [switch]$Agendada
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

# Gravacao crua no log, com posse exclusiva do arquivo e repeticao enquanto ele
# estiver tomado. "Add-Content" foi o que estava aqui e nao serve: com duas
# rodadas ao mesmo tempo ele nao reclama e nao para, ele PERDE linha calado.
# Medido em 19/09/2026 nesta maquina: tres processos gravando 400 linhas cada
# deixaram 649 das 1200 no arquivo, sem um unico erro. Foi assim que a rodada
# 'alerta' daquele dia sumiu do log inteira, sem deixar nem o "comecou".
function EscreveBruto($linha) {
    for ($tentativa = 0; $tentativa -lt 50; $tentativa++) {
        try {
            $fs = [System.IO.File]::Open($log, 'Append', 'Write', 'None')
            try {
                $sw = New-Object System.IO.StreamWriter($fs, (New-Object System.Text.UTF8Encoding($false)))
                $sw.WriteLine($linha)
                $sw.Flush()
                $sw.Dispose()
            } finally { $fs.Dispose() }
            return
        } catch {
            Start-Sleep -Milliseconds 60
        }
    }
}

# Write-Host, e nao Write-Output: o que vai para o pipeline vira valor de
# retorno da funcao que chamou, e "Invoca" passaria a devolver um array em vez
# do codigo de saida. Foi o que fez a primeira rodada de teste acusar falha num
# render que tinha terminado com 0.
function Escreve($texto) {
    $linha = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $texto
    EscreveBruto $linha
    Write-Host $linha
}

function Invoca($titulo, $argumentos) {
    Escreve "-> $titulo"
    # Python escreve aviso em stderr e isso nao e erro; com 'Stop' o 2>&1
    # derrubaria a funcao antes de ler o codigo de saida.
    $ErrorActionPreference = 'Continue'
    # A saida vai para o log linha a linha, conforme sai. Antes ela era juntada
    # numa variavel e so gravada depois que o python voltava, entao rodada
    # morta no meio (o Agendador mata no limite de tempo) nao deixava rastro
    # nenhum: em 19/09/2026 o log ficou com um "-> gerar_guia" que nunca
    # fechou, e o que a coleta tinha lido em 40 minutos se perdeu junto.
    # "-u" no python porque senao o proprio python segura a saida no buffer e
    # a transmissao aqui nao adianta nada.
    & python -u @argumentos 2>&1 | ForEach-Object { EscreveBruto ("    " + $_) }
    $codigo = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
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

# Trava de rodada: uma coleta por vez nesta maquina. O arquivo e aberto com
# posse exclusiva e so e solto quando o processo termina, inclusive quando o
# Agendador o mata no limite de tempo (o Windows fecha o descritor junto).
#
# Isto existe por causa de 19/09/2026, no PC do trabalho. As tres tarefas tem
# "StartWhenAvailable", que e o certo: maquina desligada as 07:30 nao perde a
# rodada, ela roda quando liga. So que naquele dia o PC so foi ligado as
# 14:44, e ai as duas rodadas atrasadas (07:30 e 13:00) dispararam **no mesmo
# segundo**. Duas coletas ao mesmo tempo entram no AVA duas vezes, e o
# MoodleSession da segunda derruba o da primeira; a primeira passou o resto do
# tempo tentando reabrir pagina que voltava para o login, ate o Agendador
# mata-la nos 40 minutos (codigo 0x40010004). Resultado: painel parado em
# 18/09 e ninguem soube ate o vigia das 20h.
$travaCaminho = Join-Path $logDir 'rodada.lock'
$trava = $null
function PegaTrava {
    try {
        $script:trava = [System.IO.File]::Open($travaCaminho, 'OpenOrCreate', 'ReadWrite', 'None')
        return $true
    } catch {
        return $false
    }
}

# Guarda dos gatilhos de logon e desbloqueio da tela.
#
# Medido em 22/09/2026: o notebook ficou em suspensao moderna de 21/09 22:00 a
# 22/09 15:17 e as rodadas das 07:30 e 13:00 NAO foram recuperadas, apesar do
# StartWhenAvailable (NumberOfMissedRuns 1, LastRunTime do dia anterior). O
# vigia so gritou as 15:26. Por isso diario, alerta e revisao tambem disparam
# no logon e no desbloqueio, e esta guarda decide se ainda ha o que fazer:
# antes do horario marcado nao faz nada (a tarefa do horario faz), rodada ja
# feita no periodo sai quieta, e tentativa recente nao se repete. Sai sem
# escrever no log de proposito: desbloqueio acontece dezenas de vezes por dia.
function MarcaArq($nome) { Join-Path $logDir ($nome + '.txt') }
function JaFeita($nome, $desde) {
    $arq = MarcaArq ($nome + '_feita')
    if (-not (Test-Path $arq)) { return $false }
    try { return ([datetime]::ParseExact((Get-Content $arq -Raw).Trim(), 'yyyy-MM-dd', $null) -ge $desde) }
    catch { return $false }
}
function MarcaFeita($nome) {
    Set-Content -Path (MarcaArq ($nome + '_feita')) -Value (Get-Date -Format 'yyyy-MM-dd') -Encoding ASCII
}
function TentouHaPouco($nome, $horas) {
    $arq = MarcaArq ($nome + '_tentativa')
    if (Test-Path $arq) {
        try {
            $ultima = [datetime]::ParseExact((Get-Content $arq -Raw).Trim(), 'yyyy-MM-dd HH:mm', $null)
            if (((Get-Date) - $ultima).TotalHours -lt $horas) { return $true }
        } catch { }
    }
    Set-Content -Path $arq -Value (Get-Date -Format 'yyyy-MM-dd HH:mm') -Encoding ASCII
    return $false
}

if ($Agendada -and $Modo -ne 'vigia') {
    $agora = Get-Date
    $horario = @{ diario = '07:30'; alerta = '13:00'; revisao = '10:00' }[$Modo]
    if ($Modo -eq 'revisao') {
        $desde = $agora.Date.AddDays(-(([int]$agora.DayOfWeek + 6) % 7))   # segunda desta semana
        $cedo = ($agora.DayOfWeek -eq 'Monday') -and ($agora.TimeOfDay -lt [TimeSpan]$horario)
        $espera = 3
    } else {
        $desde = $agora.Date
        $cedo = $agora.TimeOfDay -lt [TimeSpan]$horario
        $espera = 1
    }
    if ($cedo -or (JaFeita $Modo $desde)) { exit 0 }
    if (TentouHaPouco $Modo $espera) { exit 0 }
}

Push-Location $repo
try {
    Escreve "=== rodada '$Modo' comecou ==="

    if ($Modo -eq 'vigia') {
        # O vigia e a unica coisa que pega a rodada que NAO aconteceu, por isso
        # fica fora dela: se morasse dentro do diario, sumiria junto com ele.
        # Exit 0 e painel em dia, e o vigia nao fala nada; vigia que fala todo
        # dia deixa de ser lido.
        #
        # Coleta em andamento e o unico caso em que painel velho nao e defeito:
        # o retrato novo ainda esta sendo escrito. Gritar aqui seria alarme
        # falso, e alarme falso e como se mata um vigia.
        if (-not (PegaTrava)) {
            Escreve '=== vigia: tem coleta rodando agora, nao e painel congelado ==='
            exit 0
        }
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

    if ($Modo -eq 'revisao') {
        # Revisao semanal (segunda-feira): junta o material da semana que
        # terminou e monta o corpo de revisao em privado\estudo.
        #
        # Semana ja feita e tentativa recente sao barradas pela guarda do
        # inicio do script (gatilhos de logon e desbloqueio).

        # Ela tambem entra no AVA, entao respeita a mesma trava; mas, em vez
        # de desistir na hora, espera ate 40 minutos, porque na segunda ela
        # costuma cair logo atras da rodada da manha.
        $pegou = $false
        for ($i = 0; $i -lt 40; $i++) {
            if (PegaTrava) { $pegou = $true; break }
            if ($i -eq 0) { Escreve 'revisao: outra rodada lendo o AVA; espero ela terminar' }
            Start-Sleep -Seconds 60
        }
        if (-not $pegou) {
            Escreve '=== revisao: trava nao soltou em 40 min; fica para a proxima segunda ==='
            exit 0
        }
        $codigo = Invoca 'revisao_semanal' @('automacao/revisao_semanal.py')
        $resumoArq = Join-Path $logDir 'revisao_resumo.txt'
        $resumo = if (Test-Path $resumoArq) { (Get-Content $resumoArq -Raw -Encoding UTF8) } else { '' }
        if ($resumo -and $resumo.Trim()) {
            Avisa 'Univesp: revisao da semana' $resumo.Trim()
        }
        if ($codigo -ne 0) {
            Avisa 'Univesp: revisao semanal com problema' 'Veja tmp\log\rodar_diario.log.'
            Escreve "=== revisao terminou com codigo $codigo ==="
            exit 1
        }
        MarcaFeita 'revisao'
        Escreve '=== revisao terminou ==='
        exit 0
    }

    if (-not (PegaTrava)) {
        # Sair com 0 de proposito: nao aconteceu falha nenhuma, a leitura ja
        # esta sendo feita pela outra rodada. Exit 1 aqui encheria o historico
        # do Agendador de erro que nao e erro.
        Escreve '=== ja tem outra rodada coletando; saio sem ler o AVA ==='
        exit 0
    }

    # Rodada atrasada que cai em cima de outra nao precisa reler o AVA: o
    # retrato acabou de ser feito. O limite vai para 1,5h e quem responde e o
    # proprio vigia, que ja sabe medir idade de painel; escrever a conta de
    # novo aqui seria criar uma segunda versao dela para divergir da primeira.
    # Exit 0 do vigia = painel mais novo que o limite.
    if ($Modo -eq 'alerta' -and -not $SemColeta) {
        $env:LIMITE_HORAS = '1.5'
        $recente = (Invoca 'vigia (painel ja esta fresco?)' @('automacao/vigia.py')) -eq 0
        Remove-Item Env:\LIMITE_HORAS -ErrorAction SilentlyContinue
        if ($recente) {
            Escreve '=== painel lido ha menos de 1,5h; alerta nao rele o AVA ==='
            MarcaFeita 'alerta'
            exit 0
        }
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

    MarcaFeita $Modo
    Escreve '=== rodada terminou ==='
    exit 0
} finally {
    if ($trava) { $trava.Dispose() }
    Pop-Location
}
