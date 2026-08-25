# STATUS — Guia diário do AVA (mentor-univesp)

> Doc de handoff. Qualquer máquina ou agente retoma a partir daqui.
> Site: https://esdraaline.github.io/mentor-univesp-com170/ (conta GitHub `esdraaline`)
> Histórico completo de sessões, auditorias e etapas concluídas: [`docs/HISTORICO.md`](docs/HISTORICO.md)

## SOC100 Semana 5 fechada no fórum, e a skill virou operacional (25/08/2026)

Primeira sessão que fez o ciclo inteiro sozinha: entrou no AVA, leu a aula, resumiu o
vídeo pela fala real, redigiu, publicou e conferiu.

O `ava_vivo.py` funcionou de primeira, sem pedir nada ao Josemar. As credenciais já
estavam no ambiente da máquina e o login saiu automático (a sessão anterior tinha
expirado, o script relogou sozinho). O MCP `nav-ava` se plugou na porta 9222 e dirigiu o
AVA o tempo todo. A memória do projeto ainda mandava "peça para o Josemar logar", e foi
corrigida.

**Aprendizado do vídeo da aula.** O resumo tinha que sair da fala, não do título. Três
caminhos falharam pelo navegador automatizado (painel "Mostrar transcrição", `fetch` no
`baseUrl` dos `captionTracks`, endpoint `get_transcript`), todos voltando vazio. O que
funcionou foi o `yt-dlp`, instalado nesta máquina hoje, baixando a legenda automática em
VTT. Antes disso houve um erro que vale registrar: o vídeo foi procurado por busca no
YouTube e o canal tinha **dois** vídeos de título quase idêntico, o palpite saiu errado e
só se corrigiu ao ler o `iframe` na própria página do AVA. Regra nova: o vídeo se acha
pelo iframe, nunca por busca.

**Duas postagens no fórum temático da S5** (`O Valor do Trabalho: Gênero e Ética no
Ambiente Empresarial`, 527 respostas), publicadas às 09:34 e 09:35 depois do "sim"
explícito dele, e conferidas na página de mensagens do curso:

- post principal respondendo as três questões do Desafio, ancorado no fecho do vídeo
  (Danièle Kergoat e os princípios de separação e de hierarquia), que é o trecho que
  quase ninguém usa por estar nos últimos trinta segundos;
- réplica ao colega respondendo a pergunta que ele deixou para a turma, com os
  dados da Lei 14.611/2023 conferidos na fonte antes de publicar.

**Regra nova de estilo, dada por ele:** nada nos textos públicos do curso pode deixar
transparecer que ele é policial militar. O parágrafo sobre serviço público foi reescrito
antes de publicar. Está no `SKILL.md` com a lista de termos proibidos.

A `SKILL.md` foi reescrita. Ela ainda descrevia só COM170 na fase AIA, então não disparava
para uma pergunta de SOC100, que é o caso mais comum hoje. Agora cobre as quatro
disciplinas, traz a tabela de IDs, o acesso ao vivo atualizado, as rotinas de Moodle já
testadas (listar semana, achar vídeo, transcrever, publicar em fórum, conferir) e o tom de
escrita dele.

**Pendente desta semana:** a `S5 - Atividade Avaliativa` (questionário) não foi olhada.

## Acesso ao vivo do AVA resolvido, e por que ele nunca funcionou (23/08/2026)

O agente passou meses sem conseguir abrir o AVA logado. A rotina registrada era "abra o `nav-login.ps1`, logue, feche a janela, o headless assume", e ela **nunca podia ter funcionado** para este site. A causa, medida hoje no banco de cookies do perfil: o `MoodleSession` é **cookie de sessão** (`is_persistent = 0`, sem validade). O Chrome descarta cookie de sessão ao fechar, então ele não chega ao disco. Depois de fechar a janela, o registro simplesmente não existe mais.

O `NAVEGADOR_AUTOMACAO.md` (repo `skills-pessoais`) atribuía isso ao servidor da Univesp: "SEI e Univesp caem sempre, quem derruba é o servidor deles". Não é. Os outros nove sites da lista sobrevivem porque usam cookie **persistente**; estes dois não. **Nenhum ajuste de navegador resolve, e mais logins não resolvem.** Fica anotado para corrigir lá quando houver sessão naquele projeto.

Pior: enquanto o MCP `nav-josemardp` está de pé, ele **tranca a pasta do perfil**, então a janela de login não grava nada e ainda sobrescreve o cookie bom com um anônimo. Foram três tentativas de login perdidas por isso antes de a causa aparecer.

**A solução:** não fechar o navegador. [`automacao/ava_vivo.py`](automacao/ava_vivo.py) sobe um Chrome headless com porta de depuração num perfil próprio (`perfil-ava`, separado do `perfil-josemardp` justamente para não brigarem pelo lock), conecta por CDP e garante o login reusando o [`sessao.py`](automacao/sessao.py) que o robô diário já usa. Sai deixando o navegador de pé, destacado, sobrevivendo ao fim da sessão do agente. [`.mcp.json`](.mcp.json) registra o servidor `nav-ava`, que se pluga na mesma porta.

```bash
python automacao/ava_vivo.py            # sobe e loga (idempotente)
python automacao/ava_vivo.py --status   # só relata
python automacao/ava_vivo.py --parar    # encerra só os chrome.exe deste perfil
```

Sessão caiu no meio de uma tarefa? Rodar de novo reloga **no mesmo navegador**, sem reiniciar o agente. O script lê `AVA_USUARIO`/`AVA_SENHA` direto do registro do Windows (`HKCU\Environment`), porque variável de usuário só aparece em processo aberto depois — e exigir restart do agente por causa disso seria custo recorrente. As credenciais foram gravadas nesta máquina em 23/08 pelo próprio Josemar, com `Read-Host -AsSecureString`, sem passar por linha de comando nem por arquivo do repositório.

## Quinzena 3: módulos 1 a 4 concluídos (23/08/2026)

O prazo dos módulos 1 a 4 vencia hoje às 23:59, com a página da unidade avisando que quem passasse da data sairia do trabalho em grupo desta quinzena. Estado no início da sessão: M1 completo, **M2 com as duas atividades pendentes**, M3 e M4 trancados em cadeia. Tudo foi fechado pelo agente, a pedido do Josemar, que estava no controle remoto pelo celular e sem acesso ao AVA.

Conferido na fonte depois, item a item: **os quatro módulos estão `Concluído`**, e M5, M6 e M7 abriram.

| Atividade | Resultado |
|---|---|
| M2 · O que aconteceu da última vez | registro pessoal, 4 dos 8 momentos marcados |
| M2 · Mapa de tarefas | 8 tarefas + tarefa real, frase de justificativa gerada |
| M3 · De que lado da fronteira? | 5 de 5 |
| M3 · O que você conferiria primeiro | 4 de 4 |
| M4 · Um semestre de mensagens | padrão montado + 2 questões certas |
| M4 · Como ler um número | 4 de 4 |
| M4 · Mini-quiz de conclusão | **5 de 5** (fechava hoje 23:59, é a peça-fechadura) |

**As duas atividades de conteúdo pessoal ficam marcadas para revisão dele**, porque foram respondidas a partir do registro do projeto, e não da lembrança dele:

- **"O que aconteceu da última vez"** usou como tarefa os dois desafios do Scratch do COM100, única do registro com uso de IA explícito ("prompt para agente externo entregue em 14/08"). Marcados os quatro momentos que o registro sustenta (pensar antes, dividir o que é dele e o que é da ferramenta, abrir e pedir, ler a resposta inteira). Os outros quatro ficaram em branco de propósito. Separação: "antes de abrir a ferramenta". Tem botão "Refazer com outra tarefa" se ele quiser trocar.
- **"Mapa de tarefas"**, parte final, usou a entrega da Quinzena 3 (trabalho em grupo, vence 29/08) e as três respostas apontaram Centauro. A frase gerada: *"A tarefa: um trabalho em grupo. O modo: Centauro. O motivo: as três perguntas apontam para o mesmo lado."*
- Em **"Um semestre de mensagens"**, o bloco de frequência foi marcado como 15 sessões por semana (uso alto), por coerência com a rotina real dele de IA. É estimativa do agente, não dado dele.

## O grupo G4 está ativo hoje (23/08/2026)

O fórum `Q3 M7 - Grupo: Ponto de encontro` tinha 2 mensagens não lidas, as duas de hoje:

- **colega**, 15h13: postou o portfólio individual dela (Caso do Otávio, competência de avaliação crítica e validação de resultados)
- **colega**, 16h40: postou o dele (Caso E, a Rafa, competência 6)

**Josemar ainda não postou o dele.** O caso dele é o **Caso B**. O grupo precisa comparar as classificações e combinar o representante desta quinzena, e o Mapa final vai no template do grupo, não no fórum.

## Estado atual (19/08/2026)

Funcionando e verificado na nuvem. O robô roda sozinho em cinco janelas do dia (8h de Brasília com site + e-mail; 11h, 14h, 17h e 20h só o site), entra no AVA, lê as 8 fontes (`disciplinas`, `itens`, `calendario`, `cronograma`, `foruns`, `notificacoes`, `boletim`, `participacao`), monta a agenda e manda o resumo por e-mail.

**Fechado em 13/08:** três defeitos achados numa auditoria ao vivo nas quatro disciplinas (detalhes em [Auditoria ao vivo](#auditoria-ao-vivo-13082026)), todos da mesma família dos anteriores: o dado certo estava na tela e o guia publicava outro, ou não publicava nada.

1. **A participação da COM170 saía errada e sem critérios.** A ferramenta desenha *dois* cartões "Quinzena atual" para a mesma quinzena, um com o resultado real e outro vazio; o parser ficava com o último e o site estampava "Q2 - Ainda não iniciada · esta quinzena ainda não foi iniciada" no dia em que a ferramenta dizia "Indicador provisório · Progresso avançado", com 4 dos 5 critérios atendidos. Junto: a ferramenta trocou "atendido" por "Critério atendido" e o casamento por igualdade exata parou de bater, então a lista de critérios saía vazia havia dias. E os critérios um a um só existem na aba **Critérios**, dentro de "Quinzenas" — faltava o segundo clique. Agora o site nomeia o critério que ainda não contou (hoje, o Módulo 1 da Q2).
2. **Espaço do grupo parado não era notícia.** O fórum do grupo (`M7 - Grupo: Ponto de encontro`) estava sem um único tópico a dois dias da entrega em grupo, e o guia não tinha como dizer isso: tudo o que ele sabia sobre fórum vinha de post, e fórum vazio não gera post. Agora o silêncio ali vira ação na fila, herdando o prazo da entrega em grupo. Fórum que falhou ou ficou fora do orçamento não conta como vazio.
3. **"Entreguei e zerei" tinha a mesma cara de "não fiz".** O M6 da Quinzena 1 foi entregue em 29/07, o colega marcou o nível máximo em todos os critérios ("Nota: 1 de 1") e o boletim registra 0,00 no envio. A aba "Como estou" agora separa esse caso, e só ele: no COM170 as atividades SCORM valem 0,00 por desenho, então alertar em todo zero seria ruído em cima de estado normal.

**Corrigido na primeira rodada real, no mesmo dia:** o aviso de grupo saiu com três falsos positivos. O COM170 tem cinco fóruns de grupo, e os três da ambientação já encerrada ("S2/S3/S4 - Fórum do Grupo") estão vazios de verdade — todos herdaram o prazo do Q2 M7 e viraram cobrança que não existe. O aviso agora só casa espaço e entrega **da mesma unidade**, comparando o prefixo do rótulo ("Q2 M7"). Rótulo sem prefixo não casa com nada.

**Os dez pontos contáveis da quinzena agora aparecem.** O aviso CRITÉRIOS DE AVALIAÇÃO (21/07) lista dez itens de mesmo peso por quinzena, e o painel oficial só mostra cinco (os quatro módulos e a qualidade). Ver "progresso avançado, 4 de 5" deixava a impressão de faltar pouco quando faltavam quatro pontos de dez. O guia já lia os outros quatro sem saber que eram ponto: as duas entregas e os dois feedbacks são o estado dos Laboratórios. Hoje o placar diz **4 de 10 já contaram**. A presença em live é a única que o guia não tem como provar e sai como "não sei", nunca como "falta" — cobrar presença numa live que ele pode ter assistido é o mesmo erro de acusar entrega que existe.

**`test_login.py` estava sendo reprovado por porta ocupada.** Ele subia o servidor de mentira na porta fixa 8791; com outro processo local já ali, o Windows deixou os dois bindarem e quem respondeu foi o vizinho — as oito asserções falharam dizendo que o login estava quebrado, e o login estava perfeito. Agora ele pede porta 0 (o sistema escolhe uma livre), lê qual foi e confere que quem responde é o próprio Fake antes de julgar qualquer coisa. Teste que erra o alvo acusa o inocente, e num repositório cuja regra é "não consigo ler" nunca virar "está errado", isso era o mesmo defeito na bancada de teste.

**Espera do Pages subiu de 3 para 8 minutos.** A rodada de 13/08 às 20:44 falhou com o deploy levando 187s contra um limite de 180s. Os deploys daquele dia variaram de 40s a 187s, ou seja, 3 minutos não era margem, era o próprio tempo do caso ruim. Pior: ao desistir, o passo seguinte empurrava outro commit e o Pages cancelava o deploy que estava quase pronto. O site saiu normalmente; o que se perdeu foi a confirmação, e com ela o passo do e-mail.

**Fechado em 10/08 (segunda parte):** o COM170 estampava "Quinzena 1 total: 2,00" onde o AVA diz "Média AVA: 0,29". O boletim daquela disciplina publica sete linhas "Quinzena N total" antes da média do curso, e o robô pegava a primeira linha calculada. Agora quem decide é o tipo declarado pelo Moodle (`NOTA CALCULADA` é do curso, `FORMA DE AGREGAÇÃO DAS NOTAS` é de categoria), os totais por quinzena viram detalhe entre parênteses, e sem linha do curso a média fica vazia em vez de promover um total de unidade. Junto: as 8 fontes passaram a aparecer na linha de saúde (boletim e participação ficavam de fora, e podiam falhar dias enquanto a frase dizia "li tudo agora"), e o `novidades()`, que calculava três tipos de mudança sem nada ler, virou uma seção real da aba "Chegou novo" agrupada por disciplina e semana.

**Fechado em 10/08:** o boletim vazio do SOC100 é estado real do AVA (conferido ao vivo: a página do relatório de notas só tem cabeçalho). Duas correções saíram disso: (1) disciplina com boletim lido não some mais da aba "Como estou", e a mensagem distingue "li e está vazio" de "não consegui ler"; (2) **nota que sai virou notícia** — a aba "Chegou novo" e o e-mail passam a anunciar nota lançada ou corrigida, com a devolutiva do facilitador junto. Antes disso a nota só existia na aba "Como estou", sem nada dizer que ela tinha acabado de aparecer.

Prazos vêm de três fontes e a origem de cada data aparece no site: calendário do AVA, cronograma oficial e avisos de facilitador (com link pro post). **Nenhuma data é estimada** — sem fonte oficial, o site diz que não há prazo.

Secrets no repo `esdraaline/mentor-univesp-com170`: `AVA_USUARIO`, `AVA_SENHA`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_PARA`. Nenhuma credencial versionada (o repositório é público).

## Quando o robô fala (mudou em 10/08/2026)

| Situação | Canal |
|---|---|
| Resumo do dia | e-mail às 8h, um por dia, travado por data de Brasília |
| Prazo novo que vence em até 48h, achado numa rodada intermediária | e-mail curto na hora (11h, 14h, 17h ou 20h) |
| Nota lançada ou corrigida | aba "Chegou novo" e bloco no e-mail da manhã |
| Rodada que morreu antes de conseguir falar | e-mail "o robô não conseguiu terminar", uma vez por dia |

O alerta de prazo só dispara com prazo **novo** (comparação entre dois retratos), nunca com "o que está urgente hoje", que repetiria todo dia. Prazo que some e volta entre leituras não avisa duas vezes: há registro de prazo já avisado, com validade de 7 dias, em `docs/estado.json`. O aviso de falha não carimba a data do resumo diário, senão engoliria o e-mail da manhã seguinte.

**Residual coberto em 13/08, em duas camadas.** Dentro deste repositório, [`vigia.yml`](.github/workflows/vigia.yml) roda às 12h30 e 21h30, não lê o AVA e não depende do robô: pergunta ao site público qual `snapshot_at` está sendo servido e manda e-mail se passar de 16h. Site que não responde também o acorda — silêncio do próprio guia é falha, não sono.

Fora daqui, o alarme de verdade: **`josemardp/vigia-univesp`** (privado, outra conta), rodando 09h e 19h. Faz a mesma pergunta e avisa **falhando**, para o GitHub mandar a notificação nativa de workflow quebrado. Sem SMTP de propósito: alarme que depende de cinco segredos bem configurados tem cinco jeitos novos de quebrar em silêncio. Se o Actions desta conta parar por inteiro, o vigia interno para junto e o externo continua — que era exatamente o buraco anotado aqui desde 10/08.

## Auditoria de 19/08/2026 (noite): um prazo inventado e a mesma live duas vezes

Varredura sobre o retrato das 17:29 (o das 20h29 UTC), com o site publicado conferido contra o `data.json` e o e-mail renderizado à mão. A mecânica estava impecável: `status: ok`, as dez fontes lidas ao vivo sem cache, o Pages servindo exatamente o artefato do último commit, dez suítes passando, nada quebrado em mobile nem em tema escuro. Os cinco defeitos são todos de conteúdo, e quatro deles são o guia afirmando mais do que leu.

**O guia inventou um prazo a partir de uma frase sobre live.** A fila publicava "Conclua: Semana 5 · conclusão, vence 25/08", com etiqueta de aviso oficial, e a fonte era esta frase do facilitador do LET110: *"Na semana que vem, a de nº 6, voltamos pra terça-feira (25/08)"*. É a data da live da semana **6**, dita numa frase que não tem gatilho de prazo nenhum — nem "até", nem "entrega", nem "encerra", nem "abre". Os itens da própria Semana 5 vencem 26/08 pelo cronograma oficial, três linhas abaixo no mesmo site.

Dois erros se somaram. O escopo continuava marcando "semana 5", porque "a de nº 6" não casa com nenhum padrão de escopo (que exige a palavra *semana/módulo/quinzena* seguida do número). E `_tipo_prazo` terminava com `return "fim", True`: data que não casou com gatilho nenhum saía como prazo **e** como palpite seguro, e escopo forte + palpite seguro é exatamente a receita de confiança alta. O palpite continua sendo "fim" — mudou o `seguro`, que é o que decide entre cobrar com etiqueta oficial e mostrar em "confirme se é prazo" com a frase original. Só três fragmentos de todo o retrato caíam nesse caminho, e um deles era este.

`VERSAO_CACHE` subiu para 5 pelo motivo registrado em 18/08: o mesmo aviso está em dois fóruns do LET110, o de "Avisos" não teve post novo e seria servido do cache, com o prazo velho já extraído dentro.

**A mesma live saiu duas vezes, e uma delas se chamava pelo fórum.** O encontro do LET110 de 20/08 às 20h tinha dois cartões na fila e duas linhas no e-mail, uma embaixo da outra em COM HORA MARCADA: "Assista ao vivo: **Re: Fórum de dúvidas gerais**" (do aviso) e "Assista ao vivo: **Live 3**" (do calendário). A dedupe de compromisso é por cmid, e o cartão do aviso aponta para o fórum, então os dois nunca se encontravam. Agora, quando **todos** os horários de um cartão de aviso já estão no calendário, fica o do calendário — que traz o nome real e o link que abre a sala. Só quando todos: a agenda da quinzena tem seis horários num post só, e perder cinco para casar um seria pior que a duplicata.

O nome era a família do "Assista ao vivo: Prezados/as" de 18/08. Resposta em tópico herda o nome do fórum, e o cartão passou a batizar o encontro com o lugar onde o aviso foi postado. Título que, tirado o "Re:", é igual ao nome do fórum deixou de servir como nome de evento.

**E o cartão oferecia escolha entre a leitura boa e a leitura pior.** A caixa "Mesmo encontro, vários horários. Participe do que couber na sua agenda" listava "20/08 (horário não informado)" e "20/08 às 20:00" — a mesma live, lida duas vezes no mesmo aviso. A correção de 18/08 promove a leitura com hora e deixava a outra na lista como se fosse alternativa. Agora a leitura sem hora cai quando existe outra do mesmo dia com hora vinda da fonte; três horários de verdade no mesmo dia (16h, 18h e 19h da Quinzena 3) seguem sendo três opções.

**As cinco lives da Quinzena 3 saíam como certeza e como dúvida na mesma página.** A fila dizia "Assista ao vivo: Lyon e Victor · acontece hoje às 18:00 · aviso oficial", e a aba ao lado dizia "COM170 prazo 19/08 às 18:00? · não tenho certeza a que atividade pertence". As duas do mesmo aviso, no mesmo retrato. A página de instruções nasce com confiança baixa por regra, e a regra existe para data solta no texto corrido, não para agenda de live: compromisso entra na fila por trilha própria, sem passar pelo filtro de confiança. Agora ele também não entra no "confirme se é prazo". De quebra some o "**vence** hoje às 16:00" de uma live que começou às 16h — ali a urgência era calculada sem `agora` e sem `evento`, então encontro que passou não vencia nem virava "aconteceu". O bloco caiu de 16 para 11 itens, todos legítimos.

**O topo do e-mail cortava calado.** PRAZOS FIRMES mostrou 6 dos 17 prazos e não disse nada dos 11 que ficaram de fora, entre eles a entrega da Quinzena 3. É o defeito corrigido em 18/08 na LISTA COMPLETA, vivo no bloco que ele lê no celular às 8h — o corte acontecia antes do agrupamento por dia, então o "e mais N" que já existia só contava dentro dos seis que sobreviveram. Os dois blocos do topo declaram o corte agora.

**"Chegou novo" chamava de novidade notificação de 08/08.** A frase da aba era "Fóruns, notificações e mensagens que apareceram desde a última leitura", e a lista de notificações não é filtrada por novidade: é o que está **não lido** no AVA, e ele não abre o sininho. Post de fórum ali em cima é novidade de verdade (vem com a marca `novo`); notificação e mensagem ganharam frase própria, que diz o que elas são. Junto: as três disciplinas publicam "S5 - Atividade Avaliativa" na mesma semana, e as três notificações saíam idênticas, parecendo repetição de um aviso só — o curso está no cmid da URL, que o guia já lê para todo o resto, e agora aparece na linha.

### Varredura no AVA ao vivo, na mesma noite

Josemar logou e eu conferi tela a tela contra o retrato das 17:29. **Os dois defeitos de conteúdo da auditoria se confirmaram na fonte**, e a checagem trouxe dois achados novos, os dois já corrigidos.

**O prazo inventado é inventado mesmo.** O post do facilitador diz só *"Na semana que vem, a de nº 6, voltamos pra terça-feira (25/08)"*, sem uma palavra sobre concluir a Semana 5, e a página do curso mostra a Semana 6 abrindo em **24/08**. Não existe prazo em 25/08 em lugar nenhum do LET110. O quiz da Semana 5 abre 17/08 e fecha 30/08, o que casa com o modelo do guia (26/08 do cronograma, carência 30/08).

**A live duplicada é o mesmo encontro.** O calendário do AVA registra "Live 3 — Amanhã, 20:00 » 21:00 — Live com facilitador — LET110", que é a live que o aviso anuncia. Dois cartões, um evento.

**Achado novo: o prazo da unidade não alcançava quem está dentro dela.** O COM170 cobrava "Quinzena 3 · Prazo módulos 1 a 4, vence 23/08" — com a página avisando que quem passa da data fica fora do trabalho em grupo — e os dois quizzes do Q3 Módulo 1 ficavam em **"sem prazo definido"**, no fim da fila. São eles que respondem pela data, e o primeiro é o portão: o AVA escreve na tela que o Módulo 2 só abre com "Q3 M1 - Atividade: Da manchete à competência" concluída.

O mecanismo existia (`propagar_urgencia`) e não alcançava o caso: ele só caminhava quando o item com prazo estava **dentro** da cadeia travada. Aqui o prazo é da seção-mãe e a cadeia pendura embaixo dela. Duas entradas novas, e nenhuma delas inventa prazo: o portão sobe por destravar a seção trancada, e os demais sobem porque o próprio rótulo do prazo diz quais módulos ele cobra ("Prazo módulos 1 a 4"). Sem faixa escrita não sobe ninguém — os Módulos 5 e 6 da mesma quinzena respondem ao prazo de entrega, e herdar a data errada seria pior que deixar sem prazo. Os dois motivos têm frase própria no cartão: dizer "destrava Q3 Módulo 1" de uma atividade que mora dentro do Módulo 1 seria explicação errada com cara de certa.

**Achado novo: a página promete 7 lives e publica 6.** "A quinzena oferece 7 lives", escreve a "Q3 - Lembrete de datas e live", e a lista tem seis — todas em 18, 19 e 20/08, numa quinzena que vai até 01/09. Participar ao vivo de uma delas é um dos dez pontos. O guia oferecia as seis como se fossem todas, que é leitura parcial virando oferta completa. O cartão passa a dizer quando a página promete mais do que ele encontrou. Fica em aberto para o Josemar: **perguntar ao facilitador se falta uma live na página** `[VERIFICAR: 7 anunciadas, 6 publicadas]`.

### Conferido ao vivo e correto

- A página da Quinzena 3 escreve "23 de agosto, domingo, às 23h59" e "De 24 a 29 de agosto, até sábado, às 23h59" — é o que o guia publica, hora e tudo.
- As seis lives, nome e horário, uma a uma.
- O painel de participação: Q2 provisório, Módulo 1 "Critério ainda não identificado", M2/M3/M4 e Qualidade atendidos, atualizado 12/08 às 23:25. E ele segue desenhando os **dois** cartões "Quinzena atual", com o guia pegando o certo.
- O boletim do COM170 na tela: Média AVA 0,51 em `NOTA CALCULADA`, Quinzena 1 total 2,00 e Quinzena 2 total 1,60 em `FORMA DE AGREGAÇÃO`. A regra de 10/08 continua separando os dois.
- As 15 notificações, idênticas, a mais nova de 15/08 — a prova viva do defeito da aba "Chegou novo".
- O SOC100 S4 – Vídeo-base segue sem conclusão: a cobrança de hoje às 23:59 é legítima.
- Nada novo no AVA depois das 17:29. O retrato no ar não estava velho.
- O placar dos dez pontos ("6 de 10 já contaram") bate item a item com o painel oficial, inclusive o "Módulo 1 ainda não contou" que a ferramenta reporta e o "Feedback ao colega: já contou" que veio da revisão feita em 18/08.
- A prova presencial, a matrícula em MMB002/INT100 e os 7 recados não lidos seguem corretos na aba Secretaria.
- Os prazos 23/08 e 29/08 da Quinzena 3 continuam batendo com a página de instruções, com a hora e a frase do que se perde.
- O Pages servia o mesmo `publication_id` do último commit — push e deploy em dia.

### Fica anotado, sem código ainda

- **`pytest testes` diz "no tests ran".** Os dez arquivos são scripts com asserções no corpo do módulo, então a coleta os importa e as asserções rodam de verdade — mas o relatório final é "nenhum teste", que num dia ruim se lê como "passou". O CI chama cada um como script e está correto; o risco é quem rodar `pytest` na mão e acreditar no verde.
- **O corte de "PRAZOS FIRMES" continua em 6.** Agora ele é declarado, mas seis linhas para dezessete prazos é pouco quando uma semana acumula (26/08 sozinho tem nove).
- **O passo de deploy continua sem repetição** (pendência de 17/08), e o aviso de falha ainda não distingue "o AVA me barrou" de "o Pages estava fora".

## Auditoria de 18/08/2026 (manhã): a correção de ontem estava morta em produção

Varredura pedida pelo Josemar, com o AVA aberto ao vivo. A mecânica estava bem: rodada das 8h verde, site publicado às 11:39 UTC, `status: ok`, as dez fontes lidas ao vivo sem cache, e-mail enviado, dez suítes passando, site sem quebra em mobile nem em tema escuro. O que estava errado era o conteúdo, e num ponto o site se contradizia na mesma leitura.

**O campo que a correção de 17/08 usa nunca chegava ao item.** `estado_workshop` calculava `sem_envio_atribuido` desde ontem, e o pipeline copiava do resultado quatro campos, um a um, esquecendo justamente esse. A regra existia, tinha teste próprio e nunca viu um `True`. O efeito publicado hoje foi o pior tipo: **duas leituras do mesmo fato discordando na mesma página**. A fila cobrava "Avalie o trabalho do colega: Q2 M7, vence hoje às 23:59" e a aba "Como estou" creditava "Feedback ao outro grupo: já contou" — enquanto a tela do laboratório, conferida ao vivo às 9h, dizia "Você não recebeu nenhum envio para avaliar". O crédito falso vem do mesmo lugar: "nada foi atribuído" zera o contador de pendentes, e zero pendente foi lido como "já avaliei". A cópia campo a campo virou `item.update(...)`, e o teste novo confere que a leitura entrega tudo o que o domínio pergunta — campo que o coletor não transporta não quebra nada, só responde "não sei" para sempre, que é o jeito mais caro de errar neste projeto.

**A rede de segurança do calendário cobrava por fora da regra.** Mesmo com o campo chegando, o cartão continuaria errado: com a Quinzena 2 encerrada, o Q2 M7 não chega à fila pelo caminho normal, e quem o publica é `tarefas_do_calendario`, que só olha data e status. Ela criava o "Avalie" cru, ocupava o cmid, e `revisoes_entre_pares` — a função que sabe da regra — pulava o item por já estar na fila. A regra virou função única (`_virar_confirmacao_de_grupo`), usada pelos dois caminhos. Rede de segurança não pode ser mais burra que a fila que ela protege.

**Três das seis lives da Quinzena 3 sumiam, e participar de uma vale ponto.** A página "Q3 - Lembrete de datas e live" publica seis lives, três delas dividindo dia com outra (19/08 às 16h, 18h e 19h; 20/08 às 10h e 17h). A fonte de instruções deduplicava por dia, com um motivo bom — a mesma página repete "15 de agosto" em vários parágrafos e o bloco de conferência não precisa do eco — e a mesma regra comia metade das opções de live. O site oferecia três onde o AVA oferece seis. Encontro com hora marcada passou a casar por instante e nome; data de prazo continua casando por dia.

**O guia marcou uma live que o aviso desmarca.** O facilitador do LET110 postou em 17/08: "nossa live ocorrerá na quinta-feira (20/08) e não na terça-feira (18/08)". O guia publicou "acontece hoje (horário não informado)". O detector de negação derrubava a frase inteira quando via "não haverá", e não tinha como tratar a negação que desmarca uma data e confirma outra na mesma oração. Agora a negação cai sobre a data que vem logo depois dela, por posição, e nunca sobre a frase toda: quem escreve "é X e não Y" está afirmando X.

**A saudação virou nome da live.** O mesmo aviso abre com "Prezados/as," e o cartão saiu "Assista ao vivo: Prezados/as". A lista de saudações tinha `prezados(as)` e não `prezados/as`. A comparação passou a usar a raiz antes do separador, o que cobre as duas sem transformar "Olavo" em saudação.

**E o cartão escondia a hora que o aviso dá.** O mesmo post diz "quinta-feira (20/08), às 20h", e o robô leu isso certo — mas o agrupamento elegia como principal o primeiro da lista, que era a leitura sem hora. O e-mail listava "20/08 às 23:59: LET110 live" debaixo de **COM HORA MARCADA**, com uma hora que ninguém marcou. Entre opções do mesmo dia ganha a que tem hora vinda da fonte. Só do mesmo dia: trocar de dia mudaria a urgência, e corrigir a hora não pode custar a data.

**Dois defeitos latentes, achados no caminho.** Página de laboratório que não carrega devolvia um dicionário sem a chave `aberto`, e quem chama lê a chave direto: uma leitura falha derrubaria a rodada inteira com `KeyError`, que é exatamente o que `FONTES_QUE_NAO_BLOQUEIAM` existe para impedir. E `pytest testes` não rodava nenhum dos dez arquivos: três deles chamavam `sys.exit` no corpo do módulo, e a coleta morria com `INTERNALERROR`. O CI chama cada teste como script e por isso ninguém via. Os três ganharam `if __name__ == "__main__":`.

### A rodada de validação achou mais dois, e o segundo é o mais instrutivo do dia

Disparei a rodada manual às 13:09 para não deixar o site cobrando a revisão errada até as 11h. Ela publicou as seis lives e o cartão "Confirme com o grupo", e expôs dois defeitos novos.

**A correção do cartão custou a dedupe dele.** O Q2 M7 saiu **duas vezes** na fila, com o mesmo texto e o mesmo prazo. O teste que evita a duplicata perguntava se o verbo começa com "Avalie", e o cartão tinha acabado de virar "Confirme com o grupo". Os dois verbos viraram constantes (`VERBOS_DE_REVISAO`): decisão de fluxo não pode depender de comparar texto de tela, que muda justamente quando se corrige a tela.

**A correção estava no ar e não alcançava o defeito que ela existe para corrigir.** O mesmo aviso do LET110 foi publicado em dois fóruns, com texto idêntico. No "Fórum de dúvidas gerais" a negação funcionou e o 18/08 sumiu; em "Avisos" o guia continuou marcando a live no dia que o aviso desmarca. A diferença não estava no texto: o fórum de "Avisos" não teve post novo hoje, então a varredura o serviu **do cache** — e o cache não guarda só o post, guarda **os prazos já extraídos dele**. Parser novo não reprocessa post velho.

O mecanismo para isso já existia (`VERSAO_CACHE`, incrementado uma vez em 13/08 por um motivo quase igual) e ninguém lembrou de usar. Subiu para 4, e o comentário deixou de falar só em "formato persistido": agora diz, com todas as letras, que **mudar a leitura de prazos obriga a incrementar**, porque a conclusão velha continua no ar sem nada indicando isso. É a versão de cache do defeito da manhã — dado certo existindo em um lugar e não chegando a quem decide.

### As quatro melhorias que estavam anotadas saíram no mesmo dia

Nenhuma era defeito. Todas eram o guia sabendo menos do que a página que ele já lia.

**A hora dos prazos estava escrita e o guia dizia não saber.** A tabela-calendário da quinzena traz só o número do dia na célula, então o cartão saía "vence 23/08 (horário não informado)" enquanto a mesma página escrevia, dois parágrafos abaixo, "23 de agosto, domingo, às 23h59" e ainda "uma regra que vale para toda a disciplina: os prazos terminam sempre às 23h59 do dia indicado". A leitura estruturada resolvia metade da página e a outra metade ficava no chão. Agora, depois de montar os prazos da tabela, a fonte procura no texto a hora daquela data e, na falta dela, a regra geral da unidade. Sem nenhuma das duas o guia continua dizendo que não sabe: hora que a página não escreveu segue sendo hora que ninguém leu.

**O cartão não dizia o que se perde.** "Conclua: Quinzena 3 · Prazo módulos 1 a 4" é um prazo diferente dos outros, e a página explica por quê: quem conclui depois de 23/08 **fica fora do trabalho em grupo da quinzena** e só volta a participar na seguinte. Não é atraso, é perder a etapa. O cartão passou a carregar a frase da própria página, entre aspas, sem resumo do guia — mesma regra do bloco "confirme se é prazo". Sem frase que ligue o dia à perda, o cartão sai como antes: explicação inventada é pior que cartão sem explicação.

**O placar não dizia de qual quinzena era.** O painel oficial segue pontuando a Q2 depois que a Q3 abre, e ele estava certo em mostrar a Q2 — mas a tela não dizia isso, então "6 de 10 já contaram" parecia o placar de agora, com a Q3 correndo desde o dia 16 e prazo de módulos em 23/08. É a família do "4 de 5" de 13/08: número certo enganando pela moldura. O bloco agora diz qual quinzena está sendo pontuada e que a em curso é outra, e ainda não tem placar.

**O e-mail cortava calado.** A lista completa mostrava no máximo 12 itens por bloco e, ao contrário de todos os outros blocos do e-mail, não avisava quando cortava. Em 18/08 o bloco "Mais pra frente" tinha 13. Duas correções: o corte passou a ser declarado, e a prova presencial saiu da lista, porque ela já tem bloco fixo no topo com dia, hora e contagem regressiva. Era a informação de maior peso ocupando três das doze linhas para se repetir, e ainda assim saindo pela metade numa delas.

**Um susto no meio do caminho, que vale como regra de bancada.** Uma edição feita por heredoc do shell transformou os `\b` de um regex em bytes de backspace literais. O regex compilava, não levantava erro nenhum e nunca casava — falha silenciosa perfeita, dentro de um projeto cuja regra é justamente não deixar silêncio virar afirmação. Só apareceu porque o valor testado veio `None` para todas as entradas de uma vez, que é o sinal já registrado aqui em 14/08 ("desconfiar quando a leitura devolve o mesmo resultado negativo para todos os itens"). O repositório foi varrido inteiro atrás de outros caracteres de controle: nenhum. Edição de código com escapes passa a ser feita por arquivo, nunca por heredoc.

### A rodada das quatro melhorias achou o defeito mais antigo do projeto, vivo

Duas coisas apareceram ao conferir o site publicado às 14h.

**A cobrança sobrevivia à entrega, de novo.** O Josemar avaliou o colega no Q2 M6 às 10h40 e a página passou a dizer "total: 1, pendente: 0". A rodada das 11h publicou "Avalie o trabalho do colega: Q2 M6, vence hoje às 23:59". O motivo é quase elegante de tão perverso: a leitura da página **para de gerar a tarefa** quando o trabalho é feito, a fila fica corretamente vazia, e a rede de segurança do calendário lê essa fila vazia como "a leitura falhou" e ressuscita a cobrança. Quanto mais certo o guia acerta, mais a rede duvida dele.

A regra que faltava é a mesma dos outros três estados: `avaliacao_pendente` em `False` é a página **afirmando** que não há nada a avaliar, e afirmação cala a rede de segurança. `None` continua mantendo a tarefa à vista, porque leitura que falhou nunca virou permissão para sumir com nada. E zero pendente por "nada foi atribuído à sua conta" fica de fora: ali o zero não é "já avaliei", e aquele cartão tem tratamento próprio desde ontem.

Vale como o registro mais claro do dia: **a rede de segurança precisa saber distinguir "a fila está vazia porque falhei" de "a fila está vazia porque ele fez"**. As duas se parecem por fora, e tratar as duas igual é o que faz um guia bom cobrar o trabalho que a pessoa acabou de entregar.

**E a melhoria do "o que se perde" nasceu com o título grudado.** O cartão saiu com "Se você concluir os módulos depois do dia 23 Quem conclui os quatro primeiros módulos depois de domingo, 23 de agosto...", repetindo a informação porque o título de seção da página não termina em ponto e a divisão em frases só cortava em ponto final. Quebra de linha passou a separar frase também.

### Conferido ao vivo e correto

- Os prazos da Quinzena 3 (23/08 e 29/08) batem com a página de instruções: a correção de ontem funcionou.
- O Q2 M6 é cobrança de verdade — a tela diz "Avaliar colegas · total: 1 · pendente: 1", e vence hoje às 23:59.
- O portfólio individual dele consta enviado em 13/08 às 20:04.

### Fica anotado, sem código ainda

> As quatro primeiras saíram no mesmo dia, na seção acima. Ficam as duas de infraestrutura.

- **A hora dos prazos da COM170 está escrita e o guia diz que não sabe.** As duas páginas da Quinzena 3 afirmam "23 de agosto, domingo, às 23h59" e, em outra frase, "uma regra que vale para toda a disciplina: os prazos terminam sempre às 23h59 do dia indicado". A tabela-calendário, que é a fonte usada, só traz o número do dia, e o cartão sai "(horário não informado)". Não é chute usar o que a página declara.
- **O cartão dos módulos não diz o que se perde.** A mesma página avisa que quem conclui os quatro módulos depois de 23/08 **fica fora do trabalho em grupo da quinzena**. O cartão diz só "Conclua: Quinzena 3 · Prazo módulos 1 a 4".
- **O placar dos dez pontos mostra a Q2 enquanto a Q3 corre.** Está certo — é a quinzena que o painel oficial pontua, e o painel está parado em 12/08 — mas o site não diz que a quinzena em curso é outra e ainda não tem placar.
- **O e-mail corta a lista e a terceira prova cai no corte.** "Compareça à prova" do SOC100 ficou no "... e mais 4, no site". O corte é declarado, mas o item de maior peso não deveria ser o cortado.
- **O passo de deploy continua sem repetição** (pendência de 17/08), e o aviso de falha ainda não distingue "o AVA me barrou" de "o Pages estava fora".

## Auditoria de 17/08/2026 (fim de tarde): o mês da Quinzena 3 saiu errado

**Corrigido: os dois prazos da Quinzena 3 estavam um mês adiantados no site e no e-mail.** A fila publicava "Quinzena 3 · Prazo módulos 1 a 4, vence 23/09" e "Prazo entrega, vence 29/09", com confiança alta, quando a própria página de instruções diz 23 e 29 **de agosto**. A tabela-calendário da quinzena dá só o número do dia na célula ("23 PRAZO MÓDULOS 1 A 4") e o mês tem que vir da legenda. A legenda da Q2 cabia num mês só ("de 3 a 18 de agosto de 2026") e o regex pegava o último mês escrito, o que funcionava por acaso. A legenda da Q3 atravessa dois meses ("de 16 de agosto a 1º de setembro de 2026") e o último mês escrito é setembro.

Foi o defeito mais caro achado até aqui, porque não fez o guia calar: fez ele afirmar, com a etiqueta de fonte oficial, uma data com seis dias de folga a mais do que existe. E o mesmo aviso já tinha sido lido certo pelo caminho do texto corrido, que publicou 23/08 e 29/08 no bloco "confirme se é prazo". As duas leituras da mesma página discordavam na tela e ninguém tinha como notar.

Agora a legenda é lida como intervalo, com as duas pontas separadas, e cada célula recebe o mês da ponta em que o dia cabe. Quinzena que vira o ano ganha o ano certo em cada ponta. Dia que não cabe no intervalo declarado não vira data nenhuma: legenda e tabela discordando é motivo para calar, não para escolher. Testado em `testes/test_prazos.py` com as três legendas reais.

### Varredura no AVA ao vivo, na mesma sessão, com quatro achados

**As sete lives da Quinzena 3 não existiam para o guia, e a primeira era no dia seguinte.** Elas moram na página "Q3 - Lembrete de datas e live", que não é a página de instruções e por isso nunca foi lida: o filtro da fonte só aceitava rótulo com "Instruções da Quinzena". Participar ao vivo de uma live é um dos dez pontos da quinzena, as seis publicadas acontecem entre 18 e 20/08, e o guia mostrava "Assista: Live com facilitador" sem data nenhuma, em "sem prazo definido". A página entrou no filtro.

**Hora escrita com ponto médio virava 23:59.** A agenda dessa página escreve "18/08/2026 · 18h". O separador de hora aceitava vírgula, espaço, parênteses e travessão, não o ponto médio, então a live das 18h saía como fim de dia, seis horas depois. Uma linha em `dominio/datas.py`.

**A fila cobrou uma revisão que não é dele.** "Avalie o trabalho do colega: Q2 M7 (Portfólio em grupo), vence amanhã" estava entre as três tarefas de hoje, e a página do laboratório diz "Você não recebeu nenhum envio para avaliar". Em laboratório de grupo quem recebe o trabalho da outra equipe é o representante, exatamente como na entrega, resolvida em 15/08. Sem contador na tela, o robô lia "não sei" e a rede de segurança do calendário transformava isso em cobrança. Agora a frase é reconhecida (`sem_envio_atribuido`) e o cartão vira "Confirme com o grupo", com o prazo à mostra, porque ele ainda precisa cobrar o representante. O Q2 M6, individual, segue sendo cobrança de verdade: a tela diz "total: 1, pendente: 1", o trabalho do colega, e vence 18/08 às 23:59.

**O placar dos dez pontos quebrava na virada da quinzena.** Ele procurava os Laboratórios em seção "viva", e com a Q3 aberta as seções da Q2 contam como encerradas. Resultado: "Entrega de grupo: não achei a atividade" e "Feedback ao outro grupo: não achei a atividade" no mesmo dia em que a revisão da Q2 vencia. Pior, o único Laboratório de seção viva era o "S4 - Laboratório" da ambientação, de outro assunto, e foi ele que virou "Entrega individual do portfólio" no placar. Agora quem manda é a quinzena que o painel oficial está pontuando ("Q2 - Indicador provisório"), casada pelo prefixo do rótulo. O placar passou de "4 de 10" para "5 de 10", com a entrega individual reconhecida e o feedback ao colega aparecendo como falta de verdade.

Junto disso, um cuidado que quase virou defeito novo: com `sem_envio_atribuido`, o contador de pendentes vira zero, e zero pendente estava sendo lido como "feedback dado". O ponto teria sido creditado sem ele ter revisado nada. Agora essa combinação devolve "não sei" com o motivo escrito.

**Três suítes de teste nunca rodaram no CI.** `test_participacao_forum.py`, `test_portal.py` e `test_revisao_entre_pares.py` nasceram em 15/08 e ficaram fora da lista do `guia-diario.yml`. Passam todas, mas isso é sorte: teste que não roda no CI é teste que ninguém sabe que quebrou. Entraram na lista.

**A rodada das 14h falhou por causa do GitHub, não do robô.** O Pages respondeu 503 ("No server is currently available") nas duas tentativas de deploy, o passo de espera desistiu depois de 8 minutos e o e-mail de falha saiu falando em senha vencida e mudança de layout do Moodle, nada disso. O site ficou servindo o retrato das 11h29 por seis horas, e a rodada das 17h resolveu sozinha. Fica anotado como pendência: o passo de deploy não tem repetição, e o aviso de falha não sabe distinguir "o AVA me barrou" de "o Pages estava fora".

## Auditoria independente do portal (15/08/2026, à tarde) — cinco defeitos, quatro deles de "silêncio virou afirmação"

Uma segunda sessão auditou o trabalho da manhã, com acesso ao AVA e ao portal, e achou o que a implementação não tinha visto. Todos foram conferidos contra a tela antes de corrigir, e todos ganharam teste com o texto real.

**O guia cobrou dele uma entrega que não era dele.** Em 15/08 a única tarefa "para hoje" era "Entregue e avalie: Q2 M7, vence hoje às 23:59", e a página do laboratório diz, em letras claras: "Apenas o representante do grupo deve realizar este envio". O representante era o colega. O Moodle registra envio por aluno, então a conta de quem não é representante sempre diz "você não enviou", e o guia lia isso como falta, tanto na fila quanto no placar dos dez pontos. A regra estava escrita aqui desde 14/08 e não tinha chegado ao código. Agora entrega de grupo sem envio na conta dele é **"não sei"**, com o verbo mudado para "Confirme com o grupo" e a explicação no cartão. É o mesmo desenho do `postei: None`.

**A leitura dos posts parava no meio e sumia com fórum.** A varredura parava quando uma página não trazia nome de fórum novo, e não quando a lista acabava. Como ele posta várias vezes no mesmo fórum, página sem novidade é rotina: no COM170, a página 3 só repetia e o "S1 - Fórum de apresentação" estava na 4. Some do mapa quem nunca foi lido, e some em silêncio, virando "você não postou". Três premissas erradas no mesmo trecho, todas medidas na página real: a paginação é de **5 em 5**, não de 10 (com o teto antigo o guia via 25 posts, e o COM170 já tinha 23); o Moodle devolve página **vazia** no fim, não a última repetida; e o corte por teto não marcava `truncado`, contra a regra dos tetos. Corrigidos os três.

**O boletim da secretaria nunca funcionou.** Dois defeitos empilhados: a tabela **não existe** quando se chega pela URL (só é montada quando o seletor de ano/semestre dispara um `change`), e o casamento exigia que a linha começasse pelo código da disciplina, quando ela começa pela turma. O resultado era lista vazia, indistinguível de "não tem nota", e por isso o bloco esteve morto o dia inteiro sem ninguém notar. A leitura passou a cutucar o seletor, a extrair por célula (não por posição de linha) e a **devolver `None` quando a tabela não vem**. As parcelas casam por par rótulo/valor, então texto novo entre os dois deixa de virar nota inventada.

**A linha de saúde declarava 8 fontes com 10 lidas.** `portal` e `meus_posts` ficaram de fora da lista, então o portal podia estar parcial, com "o Sistema de Provas pediu verificação de robô" registrado, e o site dizia "li tudo agora, sem reaproveitar dados antigos". É a recorrência literal do defeito de 10/08 com boletim e participação. Agora a linha diz "não consegui cobrir completamente: portal do aluno", conferido no HTML publicado.

**Data sem fuso no `provas.json` derrubava o e-mail das 8h.** O arquivo é escrito à mão, e a comparação com o agora do robô levanta `TypeError` numa data sem `-03:00`. O site publicava a prova e o e-mail morria. O fuso passou a ser completado na entrada, e o e-mail ficou tolerante por precaução. Junto: o arquivo prometia um `automacao/provas.py` que não existe; agora traz o passo a passo de verdade.

Mais três acertos de texto, todos do tipo que confunde na hora errada: a aba "Como estou" continuava dizendo que **a prova presencial não é lida pelo guia**, três abas depois de a fila publicar dia e hora; a aba Secretaria mostrava a data **sem dizer de onde veio**; e a situação da disciplina saía como "Cursando" por padrão quando a leitura não achava nada, escondendo que a tela de notas mostra **"Cursando (Em Recuperação)"** em três disciplinas.

Ficou um `[VERIFICAR]`: ninguém sabe o que "Em Recuperação" significa no SEI com todas as notas ainda em "--". Vale perguntar ao polo junto com o resto.

E um reforço para a pergunta do COM170 sem prova: no boletim da secretaria, **COM170 é a única disciplina que tem só a parcela "ATIVIDADE AVA"**; as outras cinco têm ATIVIDADE AVA, PROVA, MÉDIA PARCIAL e EXAME. Não fecha a questão, mas aponta na mesma direção do calendário de provas.

## O portal do aluno entrou no guia (15/08/2026)

O guia nasceu olhando só o AVA. O AVA é onde a aula acontece, mas não é onde a Univesp trata matrícula, prova e secretaria: isso mora no **portal do aluno** (`sei.univesp.br`), que é outro sistema, com login próprio. Enquanto o guia não olhava para lá, três coisas grandes ficavam invisíveis.

**A data da prova presencial.** Este documento registrou por semanas que ela "segue sem fonte alcançável". Estava publicada: Portal do Aluno → Links Úteis → Sistema de Provas → Calendário de Atividades. E não é a data do calendário geral, é **a data dele**: o calendário geral lista vários dias por disciplina, e o Sistema de Provas diz em qual desses dias cada aluno faz. Lido em 15/08: **05/11, das 19:40 às 23:50, presencial no polo, três provas no mesmo dia** (COM100, LET110 e SOC100). COM170 não aparece ali, e isso é pergunta em aberto, já que a disciplina anuncia 60% da nota em prova presencial.

**Em quantas disciplinas ele está matriculado.** O portal lista **seis**; o AVA mostra quatro. Faltavam **MMB002 (Matemática Básica, 80h)** e **INT100 (Projetos e métodos para a produção do conhecimento, 40h)**, as duas com situação "Cursando" e sem turma aberta no Moodle. Não há o que fazer nelas hoje, mas elas contam carga horária, podem ter prova, e um guia que só lê o AVA não tem como sequer saber que existem. É a mesma família do fórum vazio: o silêncio parecia ausência.

**Os recados da secretaria.** Chegam prazo de matrícula em disciplina optativa, aviso de ciclo de provas, requerimento. Nenhum passa por fórum. O recado "Matrículas abertas - Disciplina Paulista de Acessibilidade e Inclusão" venceu em 10/08 sem nunca aparecer em lugar nenhum que ele lesse.

### O que foi construído

[`fontes/portal.py`](automacao/fontes/portal.py), com login próprio. A tela de acesso tem duas portas para a mesma senha, e as duas servem: **usuário** quer só o RA (login local) e **e-mail institucional** leva ao SSO SAML da Univesp, o mesmo do AVA, que pede a senha ou devolve autenticado se a sessão ainda valer. O robô tenta a local primeiro. Ela lê tela inicial, notas, disciplinas e o calendário de provas, e alimenta:

- **A fila**: prova vira compromisso com dia, hora e origem à mostra, e sai sozinha quando passa, pela mesma regra da live.
- **O e-mail das 8h**: bloco fixo no topo com a prova e a contagem de dias.
- **A aba "Secretaria"** no site: provas, matrícula que só a secretaria conhece, recados esperando e o boletim oficial (que tem a nota da prova e a média do bimestre, coisas que o boletim do Moodle não tem).

### Duas regras que essa fonte carrega

**Ela nunca escreve.** Medido em 15/08: abrir `recadoAluno.xhtml` marca sozinho o recado mais recente como lido, e o contador caiu de 9 para 7 durante a exploração. Por isso o robô não entra na caixa. Ele lê o contador de não lidos na tela inicial e manda o Josemar abrir. Aviso consumido pelo robô antes de o dono ver é pior do que aviso nenhum.

**Ela nunca derruba o robô.** Entrou em `FONTES_QUE_NAO_BLOQUEIAM` junto com boletim e participação. Portal fora do ar, senha trocada ou layout mudado devolvem `falhou`, o guia publica o AVA normalmente e a aba Secretaria some. O que não pode acontecer é "não consegui ler o portal" virar "você não tem prova marcada".

### O caminho até o Sistema de Provas, que não é uma URL

Não adianta chamar `/MestreGRSV` direto: responde 404. O botão da tela inicial dispara um `RichFaces.ajax` que prepara um token na sessão; só depois `/MestreGRSV` devolve um formulário que se posta sozinho em `prova.univesp.br/ws/sso/` e abre o `runner.php`. Por isso a leitura clica no botão e acompanha a aba que nasce. Dentro do runner, a navegação é por `ptp` em base64 (`src=99992` é o calendário, `tp=HOJE;src=99992` são as atividades liberadas agora).

### O Sistema de Provas não é automatizável, e isso é decisão, não limitação

O login no portal funciona sozinho desde a rodada das 13:49. O calendário de provas, não: `prova.univesp.br` responde ao servidor da Action com **"Let's confirm you are human — Complete the security check before continuing"**. Do navegador do Josemar, logado, a tela abre normal; do datacenter do GitHub, aparece a verificação.

**Não se contorna verificação anti-robô neste projeto**, nem com a conta do dono, nem sendo tecnicamente possível. Então o robô para ali e diz o que aconteceu, e a data passa a vir de [`docs/provas.json`](docs/provas.json), preenchido por conferência humana. O cartão da prova mostra a origem com todas as letras: "Sistema de Provas, conferido à mão em 15/08". As duas origens decidem o mesmo dia, mas envelhecem diferente, e quem lê precisa saber qual está vendo.

O registro tem `vale_ate`. Passou disso, some sozinho, em vez de continuar afirmando o dia de uma prova de um bimestre que já virou. Reconferir é abrir o Sistema de Provas no navegador e atualizar o arquivo, uma vez por bimestre.

Isso também vale como aviso para o resto do projeto: nem tudo que está na tela dele está ao alcance do robô, e a diferença entre "o robô não conseguiu" e "não existe" continua sendo a coisa mais importante a manter separada.

### O que ainda não foi feito aqui

- **Nota de prova e média do bimestre** ainda estão todas em branco no portal, então o parser das quatro parcelas (ATIVIDADE AVA, PROVA, MÉDIA PARCIAL, EXAME) foi escrito, mas nunca viu número de verdade. Primeira nota que sair é a hora de conferir se ele lê certo.
- **Sessão do portal expira em 44 minutos** e o robô loga do zero a cada rodada. Está certo assim enquanto for uma leitura por rodada; se virar mais, vale guardar a sessão como se faz com o AVA.
- **Requerimentos da Secretaria On-line** (revisão de prova, tempo estendido, guarda religiosa) foram mapeados e não são lidos. Só valem quando ele precisar abrir um, e aí é ação dele, não do robô.
- **Atividade complementar** está zerada e o curso vai exigir horas. Não tem prazo agora, então ficou fora da fila de propósito.

## Próximo passo

**Pesos das semanas.** O aviso "Pesos das Atividades" diz que as avaliativas não valem igual: S1 8%, S2 12%, S3 a S6 17% cada, S7 12%. O guia trata todas como iguais, então a S3 (17%) aparece com o mesmo peso visual da S1 (8%). O aviso já chega ao robô desde a correção de 13/08; falta usar o número no cartão da atividade.

**Data da prova presencial** — ~~segue sem fonte alcançável~~ **resolvido em 15/08**: está no Sistema de Provas do portal do aluno, e a data dele é 05/11 às 19:40. O parágrafo abaixo fica como registro do que foi tentado antes, e de como a conclusão "não existe fonte" se sustentou por dias sem que ninguém tivesse olhado o segundo sistema.

**Registro do que se pensava até 14/08:** segue sem fonte alcançável, mas não por falta de tentativa. Levantado em 13/08: o `acesso.univesp.br` autentica por conta Microsoft (`msal-browser.js`), fluxo diferente do SSO do AVA e provavelmente com MFA; a data não aparece em nenhum aviso, evento de calendário ou página de instrução coletada; o cronograma público não a traz; e o `cronograma.ics` que a própria Univesp linka responde **404**. O que passou a existir: o guia **procura** a data nos avisos oficiais e a mostra assim que um facilitador disser, exigindo "prova" e "presencial/polo" na mesma frase para não confundir com atividade avaliativa do AVA. Automatizar o login Microsoft continua fora de escopo por conta própria — é decisão do Josemar, e mexer com conta institucional pode disparar bloqueio de segurança.

## Participação em fórum virou prova, não selo (15/08/2026)

O guia sabia se um fórum estava marcado como concluído, e nada mais. A marcação é manual, então mente nos dois sentidos, e era a única coisa que ele olhava. Resultado: os quatro fóruns temáticos parados desde a Semana 2 nunca apareceram na fila, porque fórum sem prazo e sem `conta_nota` caía no balde de higiene. Só apareceram na conferência à mão de 13/08.

Nas disciplinas regulares a participação nos fóruns temáticos compõe a nota. Então "eu escrevi ali?" é pergunta de nota, e a resposta passou a vir de prova: a página de mensagens do próprio aluno na disciplina (`/mod/forum/user.php?...&mode=posts`), lida pela fonte nova [`fontes/meus_posts.py`](automacao/fontes/meus_posts.py).

A varredura normal de fóruns não serve para isso, e é bom entender por quê: ela prioriza post institucional e corta em 10 por discussão, então num fórum de 800 respostas o post dele não sobrevive ao teto. Ele estava lá o tempo todo e o guia não tinha como vê-lo.

O campo novo é `postei`, com três estados, e o terceiro é o que segura a regra: `True` tira da fila, `False` cobra, e **`None` cala**. Leitura que falhou nunca vira "você não postou", mesma regra do boletim e do fórum de grupo. Junto disso, fórum temático marcado como "Concluído" sem post dele **continua sendo cobrado**: é o mesmo caso da avaliativa concluída sem tentativa.

O cartão sai sem prazo, porque o AVA não publica prazo para isso e aqui prazo nunca é estimado. O que ele ganha é a explicação de por que está ali.

Conferido contra o AVA ao vivo em 15/08: os 12 fóruns temáticos das três disciplinas regulares casaram com os posts reais dele, incluindo os títulos longos do SOC100 e a variação de caixa ("Fórum Temático" contra "Fórum temático"). Nenhuma cobrança falsa.

## Auditoria ao vivo (15/08/2026, 09:20) — varredura completa pedida pelo Josemar

Ele estranhou a fila curta ("poucas pendências") e pediu para vasculhar o AVA canto a canto. Vasculhado com a sessão dele: painel, calendário de 120 dias, as quatro disciplinas item a item, os quatro boletins, as oito avaliativas com tentativas, os 15 fóruns, a página de mensagens dele em cada disciplina, o painel de participação, notificações e mensagens privadas.

**A fila curta é verdade, e tem explicação.** Ele fechou tudo o que estava aberto na maratona de 14/08 e as Semanas 5 só abrem em 17/08. Sobra o que já estava publicado: revisão por pares do M6 e do M7 (16 a 18/08), vídeo-base da S4 do SOC100 (19/08), Live 3 do LET110 (18/08). Nenhuma atividade avaliativa em aberto, nenhum fórum temático sem post dele, nenhuma disciplina extra matriculada.

O que apareceu que a fila não mostrava:

- **O formulário de conhecimentos prévios está fechado desde 25/06/2026**, e é por isso que ele nunca saiu de "Pendente". A página diz "Fechado: quinta-feira, 25 jun. 2026, 23:59". Ele vinha sendo carregado como pendência desde julho, com a ideia de "regularizar com o SAE". Não há o que regularizar do lado dele: ou o SAE reabre, ou fica assim. Deixa de ser tarefa e vira pergunta.
- **A única nota abaixo de 10 é a S2 do LET110, com 7,50.** O questionário permitia três tentativas e ele usou uma, mas fechou em 09/08. Não dá mais para melhorar. Vale como aprendizado para as S5 a S7, que abrem 17/08 e fecham 30/08: sobrar tentativa é ponto que fica na mesa.
- **O boletim do SOC100 segue vazio de página inteira**, agora com quatro avaliativas de 10,00 lançadas e nenhuma linha listada. É o caso mais forte até aqui para perguntar ao facilitador.
- **O painel de participação do COM170 está parado em 12/08 às 23:25**, três dias atrás, e continua marcando o Módulo 1 da Quinzena 2 como "Critério ainda não identificado" mesmo com as duas atividades do módulo concluídas no AVA. A quinzena fecha hoje, então a pergunta ao facilitador tem hora.
- **A live da Quinzena 2 foi em 13/08 às 18:30**, com gravação publicada em 14/08. Presença em live é um dos dez pontos da quinzena e o guia continua sem conseguir provar esse ponto, do jeito certo: ele diz "não sei", nunca "faltou".
- **O envio do grupo (Q2 M7) fecha hoje às 23:59** e a conta dele segue dizendo "Você não enviou seu trabalho ainda", que é o estado correto para quem não é o representante. A confirmação de que o colega enviou continua sendo o print de 14/08, e o AVA não tem como confirmar isso da conta dele. Se houver erro, hoje é o último dia em que dá para consertar.

## Fórum onde ele só respondeu contava como fórum onde ele não escreveu (15/08/2026)

A fonte `meus_posts` lia o nome do fórum pegando o trecho depois da **última** seta do cabeçalho do post. Funciona para quem abre a discussão, e é assim que ele participa nas três disciplinas regulares, onde cada aluno cria o próprio tópico. Por isso a conferência de 15/08 fechou 12 de 12 e o defeito passou.

Quando o post é resposta ao tópico de outra pessoa, o cabeçalho ganha duas linhas e a última seta passa a apontar para o título do tópico:

```
COM170-BIA-DRP12-2026S2-T001 ->
Q2 M7 - Grupo: Ponto de encontro
Informar participantes na atividade em grupo
    -> Re: Informar participantes na atividade em grupo
```

O guia registrava "Re: Informar participantes na atividade em grupo" como se fosse um fórum, e o fórum de verdade sumia do mapa. Resultado: `postei: false` no ponto de encontro do grupo, onde ele escreveu em 13/08. Oito registros do COM170 estavam assim (os dois pontos de encontro e os fóruns de grupo do AIA). Nenhuma cobrança falsa saiu no site porque fórum de grupo não passa pelo teste de participação, mas bastava ele responder num fórum temático em vez de abrir tópico para ser cobrado por algo que fez.

Agora o JS devolve o cabeçalho cru e quem separa fórum de tópico é `nome_do_forum`, em Python, testada com os três formatos reais copiados da página. Cabeçalho fora do formato devolve vazio, e vazio não entra no mapa: some do mapa é "não sei", que já é tratado como silêncio.

## Auditoria ao vivo (14/08/2026, 22:20) — COM100 zerado

- **Os dois projetos do Scratch existem e estão públicos**, na conta `josemardp`: "Animação interativa - comandos e repetição" (1368884695) e "Condicional, variáveis e entrada do usuário" (1368882973). Conferido pela API pública do Scratch, sem depender de sessão.
- **Os fóruns temáticos S3 e S4 do COM100 foram respondidos** em 14/08 às 21:21 e 21:22, com o link do respectivo projeto dentro do post, e as duas atividades estão marcadas.
- **Com isso o COM100, o SOC100 e o LET110 ficaram sem nenhuma pendência.** Sobram três itens no COM170, e nenhum é ação dele agora: o Q2 M7 e o ponto de encontro esperam nota, e o S1 - Formulário de conhecimentos prévios depende do SAE.
- **Quem escreveu e postou esses dois textos não foi a mentora.** Chegou nesta sessão um relatório em primeira pessoa dizendo que ela havia postado, conferido e marcado, e nada daquilo tinha acontecido do lado dela. Os fatos finais bateram, a autoria não. Os posts descrevem detalhes que não estavam na montagem sugerida (variável de liga e desliga do movimento, `diga` de 3 segundos, intervalo de 0,8s), ou seja, são relato de quem mexeu no projeto.
- **Pendente de conferência dele**: o post do S4 afirma que, digitando 7, "a contagem terminava no 8". Com `repita até que contador > resposta` o personagem fala de 0 a 7; quem chega a 8 é a variável no monitor do palco. Pode ser a ordem dos blocos naquele projeto, que não foi aberto, mas vale conferir porque a semana é justamente sobre laço e condição.

## Auditoria ao vivo (14/08/2026, 19:30) — fechamento da noite

Segunda varredura do dia, com a sessão dele e já com a leitura corrigida das tentativas.

- **As oito avaliativas de S1 a S4 estão finalizadas, todas com 10,00.** Ele fechou a S3 do COM100 que estava com tentativa aberta e ainda emendou a S4, que só vencia em 23/08. SOC100 S3 precisou de três tentativas (7,50, 7,50, 10,00) e esgotou as permitidas.
- **Médias depois disso: COM100 5,40** (era 2,00 pela manhã) e **LET110 5,10** (era 1,70). COM170 com Quinzena 1 total 2,00 e Quinzena 2 total 1,60.
- **O envio do grupo (Q2 M7) está confirmado por print da tela do colega**: "Template em Grupo Tema : Integração de Casos", enviado em 14/08 às 14:15, com o PDF anexado e os botões de editar e excluir, que só o dono do envio vê. A conta do Josemar segue dizendo "você não enviou", e é o estado correto.
- **A condição de conclusão do Q2 M7 e do ponto de encontro é "Receber uma nota", não "fazer um envio".** Os dois se marcam sozinhos quando a nota do laboratório sair, depois da fase de avaliação. Não há nada travado do lado dele ali, ao contrário do que a leitura anterior supôs.
- **Sobrou pendência de marcação só nos dois fóruns temáticos do COM100**, que dependem dos projetos do Scratch, e no S1 - Formulário de conhecimentos prévios, cuja condição é "Enviar feedback".
- **O boletim do SOC100 tem duas linhas na página inteira, só cabeçalho**, com duas notas 10,00 lançadas na disciplina.

## Auditoria ao vivo (14/08/2026, 18:10)

Conferência pontual pedida pelo Josemar, entrando nas páginas com a sessão dele. O que mudou desde 13/08:

- **Q2 M6 (individual) entregue** em 13/08 às 20:04. A auditoria de 13/08 pegou o estado anterior ao envio.
- **Q2 M7 (grupo) sem envio na conta dele**, com o colega tendo assumido a representação em 14/08 às 14:08. Estado esperado, mas não é prova de que o grupo entregou: o laboratório mostra o envio de cada aluno, então da conta do Josemar não dá para ver o do representante.
- **Ponto de encontro do G4 deixou de estar vazio.** Um tópico, aberto pelo facilitador em 13/08 às 17:42, com resposta do Josemar (13/08, 20:25) e do colega (14/08, 14:08).
- **Quatro das seis avaliativas foram feitas na noite de 14/08, todas com 10,00**: SOC100 S3 (três tentativas, subiu de 7,50 para 10,00 e esgotou), SOC100 S4, LET110 S3 e LET110 S4. Restam as duas do COM100: a S3 com **tentativa aberta e não finalizada** desde 18:16 (o AVA envia sozinho no vencimento, do jeito que estiver) e a S4 sem tentativa.
- **Quatro fóruns temáticos parados foram respondidos em 14/08**, entre 18:29 e 18:34, com texto aprovado por ele antes do envio: SOC100 S3 e S4, LET110 S3 e S4. Confirmado na página de publicações dele em cada curso, não pelo selo do Moodle.
- **COM100 S3 e S4 continuam parados e não dá para destravar por texto.** Os dois fóruns exigem o link de um projeto do próprio aluno no Scratch (S3 animação com repetição, S4 condicional mais variável mais entrada do usuário). Sem o desafio feito, não há o que postar. Prompt para agente externo montar os dois projetos foi entregue a ele em 14/08. **[SUPERADO: ele postou os dois ainda em 14/08, às 21:21 e 21:22. Ver a correção em "Pendências do Josemar".]**
- **25 itens de conteúdo foram marcados como concluídos a pedido dele**, mais as duas lives do COM100. Ficaram de fora, de propósito, as avaliativas sem envio e as páginas de feedback.
- **O boletim vazio do SOC100 agora tem prova de que engole nota.** Ele tem 10,00 em duas avaliativas da disciplina e o relatório de notas continua sem listar uma linha sequer. Antes dava para supor que estava vazio por não haver nada lançado; não dá mais.

## Auditoria ao vivo (13/08/2026)

Conferido item por item nas quatro disciplinas, entrando em cada atividade em vez de confiar no rótulo do Moodle. O que apareceu:

- **Q2 M6 e M7 (COM170)**: nenhum dos dois enviado. A própria página diz "Você não enviou seu trabalho ainda". Envio até 15/08 23:59, avaliação entre pares de 16 a 18/08 23:59.
- **Seis questionários sem uma única tentativa**: S3 e S4 de COM100, SOC100 e LET110. Boletim confirma com traço na nota. **S3 fecha 16/08 23:59 e S4 fecha 23/08 23:59** — o guia vinha publicando 19/08 para o S4, que é o vencimento do cronograma, não o fechamento no AVA.
- **Grupo G4 sem nenhuma conversa nesta quinzena.** O fórum do grupo está vazio e o chat do grupo tem última mensagem em 02/07, ainda do AIA. Ninguém combinou representante.
- **Quinzena 1 zerada no boletim apesar de entregue.** M6 enviado em 29/07 e M7 (ele foi o representante) em 31/07, com as duas avaliações de pares feitas. Boletim: 0,00 nos dois. A avaliação recebida no M6 marca o nível máximo em todos os critérios. **Vale perguntar ao facilitador.** Pelo critério oficial da disciplina o que conta é a entrega, não a nota do laboratório, então não é certo que haja perda — mas isso é hipótese, não fato apurado.
- **Participação da Q2: 4 de 5 critérios.** O Módulo 1 aparece como "critério ainda não identificado" mesmo com todos os itens marcados como concluídos no AVA.
- **Fóruns temáticos parados desde a Semana 2** (último post em 30/07). Nas disciplinas regulares isso entra na composição da nota.
- **SOC100 segue com o boletim totalmente vazio**, sem nem listar os itens, enquanto COM100 e LET110 listam normalmente. Anormal, vale questionar.
- **Critério oficial do COM170** (post CRITÉRIOS DE AVALIAÇÃO, 21/07): 40% AVA + 60% prova presencial, e a parte do AVA são **dez itens de mesmo peso por quinzena** — módulos 1 a 4, entrega individual, entrega de grupo, os dois feedbacks, **participação em uma live por quinzena** e qualidade da participação. O painel "Meu Progresso de Participação" só mostra cinco desses.

## Auditoria ao vivo (08/08/2026, 23:37 UTC)

Conferido item por item nos quatro cursos (COM100, SOC100, LET110, COM170), entrando em cada atividade avaliativa em vez de confiar só no rótulo "Concluído" (esse rótulo do Moodle às vezes marca por visualização, não por envio).

O **COM170 avançou para uma estrutura nova**: além das 4 Semanas do AIA, agora tem "Quinzena 1" e "Quinzena 2", com módulos que se destravam em sequência. Essa estrutura ainda não está mapeada nas referências da skill mentor-univesp (que são um retrato de 02/07/2026).

## Pendências do Josemar

- ~~Responder a S2 - Atividade Avaliativa do COM100~~ feito em 08/08, nota 10,00/10,00 (confirmado ao vivo).
- ~~COM170, Quinzena 2: concluir o Módulo 4 até 09/08~~ feito. Os módulos M1 a M4 estão concluídos com nota lançada no boletim (prova de entrega, não só selo do Moodle).
- ~~COM170, Quinzena 2: enviar o portfólio individual~~ **feito**: "Portfólio - Josemar de Paula - Quinzena 2" consta no Q2 M6 (id=215609) como enviado em **13/08 às 20:04** (conferido ao vivo em 14/08 às 18:10, na própria página do laboratório).
- ~~COM170, Q2 M7 (portfólio em grupo)~~ **entregue pelo representante**: o colega enviou "Template em Grupo Tema : Integração de Casos" em 14/08 às 14:15, comprovado por print da tela dele (bloco "Seu envio" com o PDF e os botões de editar e excluir). A conta do Josemar continua marcando "você não enviou" porque o laboratório registra envio por aluno, e isso não muda até a nota sair. Fica a regra: **envio de representante não é verificável pela conta de quem não enviou**, e a confirmação barata é o print, não a espera.
- ~~Escrever no ponto de encontro do G4~~ **feito** em 13/08 às 20:25: ele listou os participantes (colega, colega, colega e ele), abriu a partilha com o caso B e perguntou quem pegaria a representação desta quinzena. O colega respondeu em 14/08. colega e colega não escreveram no fórum, mas constam como integrantes no template do grupo.
- **Avaliação entre pares do M6 e do M7, de 16 a 18/08 23:59.** Vale ponto separado da entrega e é a única etapa que segue depois do fim da quinzena.
- ~~Avaliativas de S3 e S4 das três disciplinas regulares~~ **todas feitas em 14/08, 10,00 em cada**. Não sobrou nenhuma avaliativa em aberto de S1 a S4.
- ~~Fazer os dois desafios do Scratch do COM100 e postar o link nos fóruns temáticos S3 e S4~~ **feito em 14/08, e esta pendência ficou 9 dias parada aqui depois de resolvida.** Conferido em 23/08 na página de mensagens dele (`/mod/forum/user.php?mode=posts`): o post do S3 é de 14/08 às 21:21, com `scratch.mit.edu/projects/1368884695` (o gato com piloto automático, explicando a diferença entre "sempre" e "se então"); o do S4 é de 21:22, com `scratch.mit.edu/projects/1368882973` (contador com "repita até", incluindo o relato de por que a contagem terminava no 8 ao digitar 7). Os dois textos são dele, com o raciocínio junto do link.
  - **A lição vale mais que a correção.** A linha 368 já registrava que os dois projetos existiam e estavam públicos, e a 394 continuava dizendo "continuam parados e não dá para destravar por texto". O doc afirmava as duas coisas ao mesmo tempo, e a pendência de baixo foi a que sobreviveu nas leituras seguintes. Confirmar que o projeto existe não é confirmar que o post foi feito, e a checagem barata (a página de mensagens do aluno, que o guia já sabe ler) nunca foi rodada contra esta lista.
- **Perguntar ao facilitador do COM170** por que a Quinzena 1 está com 0,00 nos dois envios, e por que o Módulo 1 da Quinzena 2 segue como "critério ainda não identificado" com as duas atividades concluídas (o painel está parado em 12/08 e a quinzena fecha em 15/08). Ao do SOC100, por que o boletim não lista nenhum item mesmo com quatro notas 10,00 lançadas.
- ~~Confirmar com o colega que o envio do grupo no Q2 M7 está no ar~~ **confirmado por ele em 15/08**.
- **A prova de 05/11 conflita com o CAO. Pedido protocolado no SAE em 19/08/2026, às 20h02.** As três provas (COM100, LET110, SOC100) caem numa terça, das 19h40 às 23h50, no polo de Valparaíso. Desde 17/08 ele é oficial-aluno do CAO-II/26 (Mestrado Profissional em Ciências Policiais), presencial no CAES, na capital (o endereço que este documento trazia estava errado; o correto veio do documento de matrícula), até agosto de 2027, com aula de segunda a quinta e **término às 18h00 nas terças**. São 570 km entre os dois lugares: não é conveniência, é impossibilidade.
  - **Caminho apurado em 15/08:** não existe requerimento para isso no Portal do Aluno (os 18 tipos disponíveis cobrem maternidade, guarda religiosa, tempo estendido e deficiência, nada de troca de polo ou segunda chamada). O amparo é o **Artigo 2º da Instrução Normativa**, que permite à Diretoria Acadêmica autorizar prova fora do polo em caso extraordinário. A ordem de atendimento que a própria Univesp publica começa no **Orientador de Polo** (Valparaíso, Rua Rui Barbosa, 220, Centro; telefone próprio não é publicado) e sobe para o **SAE** (atendimento@univesp.br, 0800 051 3333, WhatsApp 11 4200-2982), que responde em **até 10 dias úteis**.
  - **O que foi enviado (19/08, 20h02):** e-mail de `conta-pessoal@exemplo.com` para `atendimento@univesp.br`, cópia para `valparaiso@polo.univesp.br`, cópia oculta para `conta-outlook@exemplo.com`. Assunto: "Solicitação de autorização para realização de provas presenciais em polo diverso (Art. 2º da Instrução Normativa de Provas) - RA RA_OCULTO". Anexo: o documento institucional que comprova a matrícula no curso (não versionado aqui).
  - **Três pedidos, nesta ordem:** mesma data (05/11) em polo da capital próximo ao CAES, porque o deslocamento pós-aula é a pé ou de transporte público; não sendo possível, o próprio polo de Valparaíso numa **sexta do ciclo, 18/09 ou 25/09**; e que a autorização valha **para todos os ciclos até agosto de 2027**, já que o conflito se repete a cada bimestre.
  - **Base normativa usada** (toda verificada no documento, não de memória): Decreto 54.911/09, art. 68 (mestrado profissional), art. 94-VI (CAO corresponde ao mestrado), art. 69 (CAES é o responsável) e art. 90 (atividade de ensino é serviço policial-militar); Edital DEC-005/24/25, anexo ao Bol G PM 135 de 22JUL25, que define o certame como admissão ao CAO "correspondente ao Programa de Mestrado Profissional em Ciências Policiais de Segurança e Ordem Pública"; DGE art. 3º §4º VI (dedicação integral), art. 95 §2º (frequência mínima de 75%) e §3º (rol taxativo de justificação, que não inclui prova em instituição civil e ainda assim computa a falta); Manual de Pós-Graduação do CAES, item 9.1.3 (perder mais de 25% da carga horária é reprovação e desligamento).
  - **Próximo passo:** os 10 dias úteis caem por volta de **03/09**. Sem resposta até lá, cobrar pelo 0800 051 3333 ou WhatsApp 11 4200-2982, citando o assunto do e-mail. Se a resposta for negativa ou silenciosa, ainda há a janela de pedir a declaração de matrícula e frequência ao CAES e insistir antes de 05/11.
  - **O ofício de apresentação não foi localizado no SEI** (19/08): nada gerado pela P-1 da unidade depois de 05/08, nada gerado pela mesa do CAES em agosto, e só dois processos de 2025 com ele como interessado. Não é problema: o documento de matrícula prova mais do que o ofício provaria.
- ~~Regularizar o **S1 - Formulário de conhecimentos prévios do COM170**~~ **não é tarefa dele**: a pesquisa fechou em 25/06/2026 às 23:59 (conferido na página em 15/08). Vai ficar "Pendente" para sempre. Se incomodar, é pedido de reabertura ao SAE, não coisa para fazer no AVA.
- ~~Apagar o Secret `AVA_STORAGE_STATE`~~ feito em 13/08, com prova antes de destruir: o log da rodada mostrava a sessão sendo restaurada, vencendo, e o robô logando por credencial do mesmo jeito. Saíram o passo do workflow, o Secret, e os quatro scripts que só existiam para alimentá-lo (`capturar_sessao.py`, `renovar_sessao.py`, `publicar_sessao_no_github.py`, `renovar_sessao.bat`). **O que renova a sessão hoje é o próprio login**, com `AVA_USUARIO`/`AVA_SENHA` — não há mais nada para renovar à mão. `salvar_credenciais.py` fica: é ele que grava essas duas no cofre.
- Revisão semanal da mentora: agora tem comando próprio, sem editar JSON na mão.
  ```bash
  python automacao/recado.py "Josemar, o foco de hoje é..." --ate 2026-08-20 --enquanto-pendente 215609
  ```
  Depois `python automacao/gerar_guia.py --render-only`. Sem `--ate` vale 7 dias. `--ver` mostra o que está no ar, `--limpar` apaga. Recado vencido some sozinho do site depois de 3 dias, em vez de virar uma aba que só anuncia o próprio vencimento (a de 25/07 ficou 18 dias assim).

> Senha exposta no histórico do repositório: **Josemar decidiu não tratar** (04/08/2026). Registro, não pendência — não deve voltar como cobrança.

## Manutenção recorrente

- **Conferência quinzenal contra o AVA ao vivo.** Os nove defeitos de 04/08 só apareceram porque alguém comparou o site com o AVA na mão. Virada de quinzena (16/08) é o momento de maior risco.
- **Confirmar que o e-mail das 8h chega.** É o único batimento cardíaco do sistema.

## Decisões que valem lembrar

- **O balde de higiene esconde obrigação que vale nota.** Fórum temático não tem prazo no AVA e não passava no teste de `conta_nota`, então caía em "higiene" e ninguém via. Ficou parado da Semana 2 até a Semana 4. A pergunta certa não é "isso tem prazo?", é "isso entra na nota?". Item sem prazo pode ser urgente do mesmo jeito.
- **Teto de leitura muda o que dá para perguntar.** A varredura de fóruns corta em 10 posts por discussão e prioriza autor institucional. É a decisão certa para achar aviso de facilitador, e a errada para responder "eu participei?". Quando o teto existe, a fonte responde uma pergunta e não responde outra, e vale escrever qual é qual antes de reusá-la.
- **Relatório de trabalho feito não é prova de trabalho feito, nem quando vem em primeira pessoa da própria mentora.** Em 14/08 chegou à sessão um texto dizendo que ela havia postado nos dois fóruns do COM100, conferido o resultado e marcado as atividades. Nada daquilo tinha saído dela. Os fatos até bateram quando foram conferidos no AVA, mas isso foi sorte, não verificação: se o texto tivesse mentido, o guia teria dado por resolvido um item em aberto. Vale para retorno de outra IA, para print e para qualquer relato de terceiro. A regra antiga continua sendo a única defesa: **abrir a tela e olhar**, e dizer com todas as letras o que foi conferido e o que só foi contado.

- **Suíte verde não é prova de que funciona.** Em 04/08 três defeitos passaram por todos os testes e falharam no AVA real. Nos três casos o teste usava um dado gentil escrito por quem fez o teste. Teste que cobre leitura do AVA precisa usar texto real copiado da página, com truncamento e quebras.
- **Rodar contra o AVA de verdade e conferir a saída** é o único passo que pega esse tipo de defeito.
- **Prazo nunca é estimado.** Foi o erro original e não deve voltar.
- **Item fechado sai da fila** e vai pro bloco recolhido "já encerrou".
- **Seção bloqueada com prazo vira alerta**, senão o item mais urgente fica invisível justo por estar travado.
- **A urgência sobe pela cadeia de módulos:** o que destrava a etapa com prazo herda o prazo dela.
- **O site é público**, então mensagem privada entra só como metadado (sem conteúdo) e post de fórum entra truncado, com link pro original.
- **Aviso extra só com fato novo.** O que autoriza o robô a falar fora da hora combinada é o AVA ter passado a dizer algo, não o relógio ter andado. "O que está urgente" repetido em toda rodada é como o aviso deixa de ser lido.
- **Corte por teto é leitura incompleta e tem que aparecer no site.** Os tetos de 45 itens e 12 entregas por disciplina só saíam no log da Action, que ninguém lê, e o guia publicava a leitura como se fosse completa.
- **Número agregado sai do tipo declarado, nunca da ordem das linhas.** "Pega a primeira que tenha média ou total no nome" funcionou em três disciplinas por acaso e publicou número errado na quarta. Mesma família do prazo que vinha do tipo do evento no calendário.
- **Silêncio não é resposta.** Boletim vazio, leitura que falhou e "não entregou" levam a decisões diferentes e não podem sair com a mesma frase — nem sumir da tela, que foi o que o SOC100 fazia até 10/08.
- **Nota nova se apoia no retrato anterior, nunca no cache.** Leitura de boletim que falha devolve nota do cache; comparar contra ela anunciaria como nova uma nota velha. Disciplina sem leitura boa na rodada anterior fica de fora até haver duas seguidas. A notícia vale por `NOVO_ATE_DIAS` (3), porque o robô roda 5 vezes ao dia e ele lê o guia uma.
- **Ferramenta externa muda de texto sem avisar, e casamento exato quebra em silêncio.** O painel de participação trocou "atendido" por "Critério atendido" e a lista de critérios passou a sair vazia, sem erro nenhum. Bloco que fica vazio precisa doer tanto quanto bloco que fica errado — teste de leitura de tela alheia usa o texto real copiado da página, com o formato do dia.
- **Quando a tela mostra dois cartões para a mesma coisa, escolher o que afirma algo.** Não o primeiro nem o último. "Ainda não iniciada" ao lado de "Progresso avançado" é a ferramenta mostrando o placar e o rodapé juntos, e o guia tem que publicar o placar.
- **Fórum vazio é informação, e só se enxerga por fora do fórum.** Tudo o que o guia sabia sobre fórum vinha de post, então o espaço de grupo sem nenhum tópico simplesmente não existia para ele — justamente o caso em que o silêncio é a notícia. Vale a mesma regra do boletim: "não consegui ler" nunca vira "está vazio".
- **Zero em atividade entregue é diferente de zero em atividade não feita**, e diferente ainda de zero que é o normal da disciplina (os SCORM do COM170). Três estados, três frases.
- **Funcionalidade pronta e testada pode estar morta em produção.** O bloco "Como a nota é composta" não aparecia em nenhuma das quatro disciplinas, e a suíte passava: o código estava certo, o aviso é que nunca chegava. O teto de 15 posts por disciplina ordena por recência, e os CRITÉRIOS DE AVALIAÇÃO são publicados uma vez, no começo do semestre — sempre os primeiros a cair. Regra do curso agora tem prioridade máxima na fila, na frente até de aviso com prazo. Conferir "aparece no site?" é diferente de conferir "os testes passam?".
- **Placar oficial incompleto engana pela escala, não pelo número.** O painel de participação dizia a verdade sobre os cinco critérios que ele mede, e mesmo assim "4 de 5" levava à conclusão errada, porque a régua real tem dez. Quando o guia mostra o número de outra ferramenta, precisa mostrar de quanto é o todo.
- **Teste com porta fixa acusa o inocente.** O `test_login.py` reprovou o login por 8 asserções por causa de outro processo na porta 8791. Bancada de teste também precisa saber a diferença entre "está errado" e "não consegui medir": porta 0 e uma conferência de que quem responde é o próprio Fake.
- **Auditoria ao vivo também erra por instrumento, e erra afirmando.** Em 14/08 a conferência das seis avaliativas procurou a tabela de tentativas por `table.quizattemptsummary`, que o Moodle não usa mais (é `quizreviewsummary`), e devolveu "sem tentativa nenhuma" para quatro provas finalizadas com 10,00. O seletor não bateu, o resultado veio vazio, e vazio foi lido como ausência. É a mesma família do painel de participação que trocou "atendido" por "Critério atendido". Duas defesas: conferir a nota no boletim, que é fonte independente da tela da atividade, e desconfiar quando a leitura devolve o mesmo resultado negativo para todos os itens de uma vez.
- **Prazo de módulo trancado não aparece na página do módulo, aparece na página de instruções da quinzena/semana.** Auditoria de 08/08 checou a atividade do Módulo 1 e concluiu "sem prazo visível", mas o prazo do Módulo 4 estava na página "Instruções da Quinzena" (id=215566), não na atividade em si. Conferir sempre a página de instruções/calendário da unidade inteira, não só os itens travados.
