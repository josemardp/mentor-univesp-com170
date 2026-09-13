# Histórico — mentor-univesp

> Conteúdo integral do `STATUS.md` até 08/08/2026, preservado quando o STATUS foi enxugado.
> Nada foi removido: sessões, auditorias e etapas concluídas estão todas aqui.
> O `STATUS.md` passou a responder só "onde estamos e qual o próximo passo".

---

# STATUS — Guia diário do AVA (mentor-univesp)

> Doc de handoff. Qualquer máquina ou agente retoma a partir daqui.
> Site: https://esdraaline.github.io/mentor-univesp-com170/ (conta GitHub `esdraaline`)

## Última sessão: 04/08/2026 — inspeção geral contra o AVA ao vivo

Josemar pediu conferência do site contra o AVA de verdade. Sete defeitos
encontrados abrindo o AVA no navegador e comparando item por item com o
`data.json` do dia. Todos corrigidos.

**1. Seção sem título era descartada — e sumiam os Módulos 1 a 7.**
O nome de uma sub-seção colapsada mora num `<a>` em linha própria, então o
`innerText` começa com `\n` e o antigo `split('\n')[0]` devolvia string vazia.
`JS_CURSO` filtrava `s.title` vazio, então a Quinzena 1 inteira (Módulos 1 a 7)
saía do retrato. Consequência real: o Laboratório de Avaliação do Módulo 7,
ainda pendente, não existia como item — a cobrança só sobrevivia pelo aviso do
facilitador, sem link e sem hora. Agora o título vem de `data-sectionname`, com
o texto visível como reserva.

**2. Laboratório de Avaliação sumia inteiro depois da entrega.**
São duas obrigações em sequência, com prazos diferentes: entregar e avaliar o
trabalho de outra pessoa. O código pulava o item assim que `enviado` era `True`.
Em 04/08 isso escondeu justamente a avaliação do M7, que vencia naquele dia.
`fontes/itens.estado_workshop()` passa a ler também o contador "Avaliar colegas
— total: N pendente: M"; o item só sai da fila quando as duas fases fecham, e
troca o verbo para "Avalie" enquanto falta a segunda.

**3. Encontro que já começou continuava na fila.**
A live das 14h ainda aparecia como "acontece hoje às 14:00" às 17h30, porque a
comparação era só de data. `urgencia_de` passa a receber `agora`.

**4. Seis horários da mesma live viravam seis compromissos.**
O aviso dizia o contrário do que o guia mostrava: "participem da live que
melhor se adequar à sua disponibilidade". Compromissos do mesmo post viram um
cartão só, com o próximo horário na frente e os demais listados dentro.

**5. Calendário só era lido pela API — que esconde live.**
`core_calendar_get_action_events_by_timesort` só devolve atividade com pendência
do aluno. Evento de curso (a live de tira-dúvidas do facilitador, toda segunda
às 20h) e atividade já concluída nunca voltavam por ali, e o DOM só era
consultado quando a API vinha vazia. As duas leituras agora são somadas
(`calendario.unir`), e evento de agenda sem atividade correspondente vira
compromisso na fila.

**6. Duas linhas idênticas para a mesma obrigação.**
O facilitador postou o mesmo lembrete em dois fóruns no mesmo minuto. Agora
uma obrigação, uma linha: quando o aviso e o item do AVA falam do mesmo dever no
mesmo dia, fica o item (tem link, hora exata e nome real) herdando o link do
aviso. Sem item coletado, o aviso continua sendo a rede de proteção.
`rotulo_fase` passou a resumir rótulo longo preservando começo e fim, pra que
obrigações de verdade distintas não colapsem (proteção da rodada 3).

**7. Prazo da quinzena não era lido em lugar nenhum.**
As datas da Quinzena 2 (Módulo 4 até 09/08, envios até 15/08, revisão entre
pares até 18/08) só existem na página "Q2 - Instruções da Quinzena 2", que o
robô não abria — e as atividades da quinzena apareciam como "sem prazo
definido". `fontes/instrucoes.py` passa a ler essa página. Como texto corrido é
onde este projeto mais errou, **nada dali entra na fila**: nasce com confiança
baixa e cai em "Confirme se isto é prazo mesmo", com a frase e o link.

**8. (achado na primeira rodada real) Laboratório em avaliação virava
"encerrado".** Com os Módulos 6 e 7 finalmente no retrato, a rodada
[`30950643628`](https://github.com/esdraaline/mentor-univesp-com170/actions/runs/30950643628)
mostrou o M7 em "já encerrou" no dia em que a avaliação vencia. Causa:
`item_aberto()` marca como fechado quem tem "o prazo de envio terminou" na
página — frase que as **instruções da fase de avaliação** repetem
("o prazo de envio terminou e o sistema já lhe atribuiu o trabalho de um
colega"). Workshop não passa mais por `item_aberto`: `estado_workshop()`
decide pela linha do tempo das 5 fases.

**9. Sobra de quinzena antiga voltava como tarefa.** Com a Quinzena 1
visível de novo, o tutorial do Laboratório e o fórum "Ponto de encontro"
(sem data, quinzena já encerrada) entraram em "sem prazo definido".
`quinzenas_encerradas()` manda para "já encerrou" o que não tem prazo numa
quinzena anterior à atual — obrigação com data, como a avaliação por pares
que atravessa a virada, continua cobrada.

Testes novos em `testes/test_operacao.py` (leitura do AVA, união do calendário,
encontros, quinzena encerrada) e `testes/test_workshop_enviado.py` (fase de
avaliação por pares, laboratório em avaliação não é encerrado). Suíte inteira
verde, inclusive o teste dourado.

Resultado conferido contra o AVA: a fila do dia ficou com **uma** linha para
hoje (avaliação do M7, com link), a live de amanhã com os horários
alternativos dentro do cartão, a live de tira-dúvidas de 10/08 e os prazos da
Quinzena 2 no bloco de conferência.

### Rede de segurança do calendário (a correção que vale mais que as nove)

Os nove defeitos acima têm a mesma forma: uma atividade com data marcada no
AVA não chegou à fila. Mudou a seção, mudou a fase do laboratório, mudou o
jeito de anunciar — e a leitura da disciplina falhou de um jeito novo. Corrigir
cada caminho não impede o próximo caminho novo de falhar.

Por isso o calendário deixou de ser enfeite do item e virou fonte por conta
própria (`tarefas_do_calendario`): **prazo futuro no calendário que não virou
tarefa, vira tarefa**, com link e verbo, marcada com o selo "achei no
calendário". Vale mesmo que a seção não tenha sido lida, mesmo que o item tenha
sido classificado como encerrado.

O que ela **não** ressuscita: atividade com selo "Concluído", laboratório
entregue e avaliado, e sobra de quinzena encerrada — as três razões pelas quais
um item sai da fila *por estar pronto*. Item que saiu por leitura duvidosa ("o
AVA diz que não está aberta") fica fora dessa lista de propósito: era
exatamente o caso do M7.

Isso troca o modo de falhar. Antes, leitura nova quebrada = prazo invisível.
Agora, leitura nova quebrada = tarefa duplicada ou com nome feio, nunca
ausente. Continua valendo só para o que o calendário do AVA conhece — prazo que
só existe em aviso de fórum ou em página de instruções segue dependendo da
leitura de texto, e é por isso que esses vão para "confirme se é prazo".

**Segurança:** `MEMORIA.md` estava versionado com a senha do AVA em texto puro
num repositório público. Removida do arquivo, mas **continua no histórico**: a
senha precisa ser trocada.

## Sessão 30/07/2026

Layout do site virou abas (`render.py`). Antes era tudo empilhado numa
coluna só (Recado, O que fazer agora, Confirme se é prazo, Chegou novo,
Mapa das disciplinas, Higiene, Já encerrou); agora cada bloco é uma aba, e
só existe aba pras seções que têm algo pra mostrar. Aba padrão ao abrir é
"O que fazer agora"; a URL guarda a aba escolhida no hash (`#higiene` etc).
`render_higiene`/`render_encerrados`/o aviso de recado arquivado perderam o
`<details>` porque a aba já faz esse papel de "recolhido por padrão".

Primeira versão usava `overflow-x:auto` (rolagem horizontal) na barra de
abas. Josemar reportou com print que em tela larga a última aba ficava
cortada, sem indicação de que dava pra rolar. Trocado para
`flex-wrap:wrap`: as abas quebram em linhas em vez de exigir rolagem.
Testado em 1600px, 900px e mobile (375px), claro e escuro.

Teste novo em `testes/test_operacao.py` (seção "Abas") cobre: abas fixas
sempre presentes, abas condicionais somem quando vazias, contagem do selo
bate com o número de itens.

## Sessão anterior — 30/07/2026 (Módulo 6)

Josemar reportou, com print do próprio guia, que o Módulo 6 aparecia como
pendente ("Entregue o trabalho: Módulo 6 · Fechamento das submissões") mesmo
ele já tendo enviado o Portfólio Individual no AVA. Causa raiz, achada lendo
o código com ele:

- A ação nascida do **aviso do facilitador** (`dominio/acoes.py`, casamento
  por `casar_prazos`) nunca abre a atividade — só compara a data do aviso com
  hoje. Não tinha como saber que ele já enviou.
- A ação nascida do **item do curso** confiava no selo "Concluído" do Moodle,
  que num Laboratório de Avaliação (workshop) só fecha quando as 5 fases
  terminam pro aluno — inclusive avaliar o trabalho de outro grupo, que só
  abre dias depois. Enviar a parte individual não muda esse selo.

Corrigido:

- `fontes/itens.py`: nova função `envio_workshop()`, que abre a página real
  do Laboratório e lê a seção "Meu envio".
- `pipeline.py`: chama essa função pra todo item tipo `workshop` e grava o
  resultado em `item["enviado"]`.
- `dominio/acoes.py`: as duas trilhas de ação agora respeitam esse campo. A
  do aviso suprime só a fase de **entrega**, mantendo a de **avaliação por
  pares** (é uma obrigação separada, só some quando o próprio processo de
  avaliação também estiver feito). A do item some assim que `enviado is
  True`.
- `testes/test_workshop_enviado.py`: casos novos cobrindo a leitura da
  página e as duas trilhas. Suíte inteira rodada de novo, sem regressão —
  inclusive o teste dourado.

**Validado direto na Action (`workflow_dispatch`), duas rodadas:**

1ª rodada publicou e o Módulo 6 continuou na fila. Causa: os sinais de
"enviado" (`editar envio`/`excluir envio`) são da tela de edição
(`submission.php`), mas o link do curso aponta pra `view.php`, que mostra
outro resumo — não tem esses botões. Texto real de `view.php` depois do
envio: a linha do tempo troca "Tarefas a fazer" por **"Tarefa realizada"** e
aparece o carimbo **"enviado em \<data\>"** junto do título do envio. Sinais
corrigidos para essas duas frases (mantendo as antigas como reforço).

2ª rodada (`publication_id 2026-07-30T14:13:52`): `item["enviado"]` leu
`True`, a obrigação de entrega sumiu da fila e a de avaliação por pares
(04/08) continuou — exatamente o esperado. Site em produção reflete a
correção.

**Layout em abas.** Josemar pediu pra separar a página, que era uma coluna
vertical só, em abas: Recado · O que fazer agora · Confirme se é prazo ·
Chegou novo · Mapa das disciplinas · Higiene do AVA · Já encerrou. Cada aba
só existe se tiver conteúdo (Recado/Confirme/Higiene/Encerrados somem
vazias, como já sumiam antes). Aba padrão ao abrir: "O que fazer agora".

- `render.py`: nova `render_tabs()` monta a barra de abas + painéis; os
  `<h2>` redundantes dentro de cada bloco saíram (o rótulo da aba já diz o
  nome); `render_higiene`/`render_encerrados`/o aviso de recado arquivado
  perderam o `<details>` próprio (a aba já é o mecanismo de esconder).
  CSS e JS (troca de aba + hash da URL) adicionados ao `TEMPLATE`.
- Testado com o `data.json` real do dia: badge da aba Higiene bateu com o
  "7 itens" que o Josemar via na coluna antiga. Testado em mobile (375px) e
  tema escuro via browser antes de subir.
- `testes/test_operacao.py`: seção nova cobrindo `render_tabs` (abas
  condicionais, contagem do badge, painéis nascem `hidden`).

## Sessão 25/07/2026

Reestruturação completa da automação. O guia antigo cobrava tarefa que já tinha
fechado, não avisou da live de 23/07 e inventava prazo ("semana = 7 dias" fixo
no código). Foi reescrito de ponta a ponta.

- `coletar.py` (novo): descobre as disciplinas sozinho em "Meus cursos", lê a
  página de cada curso pelo DOM do Moodle, o cronograma oficial da Univesp, o
  calendário, todos os fóruns (incremental), notificações e mensagens.
- `render.py` (novo): site abre com a agenda no imperativo, em ordem de urgência.
- `sessao.py` (novo): login automático no AVA, sem renovação manual.
- `enviar_email.py` (novo): resumo diário por e-mail junto com a atualização.
- `gerar_guia.py`: virou wrapper fino, mantém `--render-only` e o `.bat` antigos.

Quatro bugs achados e corrigidos com o robô já rodando de verdade:

1. Data de abertura virava prazo ("Módulo 6 vence 27/07" quando 27/07 era o dia
   em que ele abria). Agora cada data lida de aviso é classificada início/fim.
2. Aviso de fórum sumia no dia seguinte, levando junto o prazo extraído dele.
   Agora os avisos ficam em cache por 45 dias; o selo "novo" dura 3 dias.
3. Calendário voltava vazio: eu pedia 200 eventos e o Moodle recusa acima de 50.
4. Login falhava: a Univesp usa duas telas (e-mail no AVA → SSO SAML em
   login.univesp.br), não o formulário padrão do Moodle.

## Estado atual

Funcionando e verificado rodando na nuvem. O robô roda todo dia às 8h, entra no
AVA sozinho, lê as 6 fontes, monta a agenda e manda o resumo por e-mail.

Prazos vêm de três fontes, e **a origem de cada data aparece no site**: calendário
do AVA, cronograma oficial e avisos de facilitador (com link pro post). Nenhuma
data é estimada: sem fonte oficial, o site diz que não há prazo.

Secrets configurados no repo `esdraaline/mentor-univesp-com170`: `AVA_USUARIO`,
`AVA_SENHA`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_PARA`.
Nenhuma credencial no repositório (ele é público).

## Auditoria independente (25/07/2026)

Uma segunda IA auditou o projeto com acesso ao AVA. Relatório em
`AUDITORIA-INDEPENDENTE-2026-07-25.md`. Achados aceitos e já corrigidos:

- **Falhava aberto:** coleta vazia era gravada como `ok` e o site dizia "tudo
  em dia". Agora há contrato de saúde: leitura suspeita preserva o último
  retrato válido, marca `coleta_incompleta` e deixa a Action vermelha.
- **Obrigação de duas fases perdia a segunda:** a entrega em grupo (01/08)
  aparecia, a avaliação por pares (04/08) não, e ela vale nota. Cada fase
  virou uma ação própria, com escopo lido do aviso ("Módulo 6 e 7").
- **Prazo de aviso contaminava a seção inteira**, dando data de entrega a
  material opcional. Prazo de item agora só vem de calendário ou cronograma.
- **Propagação de urgência era palpite:** herdava prazo de qualquer seção de
  número maior. Agora segue a cadeia real de "esteja marcada como concluída",
  e herda **prioridade**, nunca prazo. O item continua sem `prazo`.
- **Horário inventado:** "até 26/07" virava "26/07 23:59". Agora, sem hora na
  fonte, o site escreve "horário não informado".
- **"LIVE INICIAL" virava abertura**, porque `inicia` casava dentro de
  `inicial`. Gatilhos passaram a respeitar limite de palavra.
- **Sem testes versionados.** Agora `testes/` roda na Action antes de tocar
  no AVA.

## Auditoria rodada 2 (25/07/2026)

Segunda auditoria, focada em derrubar as correções da rodada 1. Relatório em
`AUDITORIA-INDEPENDENTE-RODADA-2-2026-07-25.md`. **Sete achados, todos
reproduzidos e todos corrigidos:**

- **Escopo do aviso não era encerrado.** "Módulo 4: até 26/07" seguido de
  "LIVE MAGNA: 30/07" e "Prova presencial: 10/09" colava as três datas no
  Módulo 4. Rótulo de assunto novo agora encerra o escopo, e o casamento de
  reserva olha só o rótulo, não a frase de contexto.
- **Início/fim classificado pela frase inteira.** Em "A abertura ocorre em
  27/07 e o prazo fecha em 01/08" as duas viravam abertura e o fechamento
  sumia. Agora cada data usa a palavra que vem antes dela. "abre"/"fecha"
  passaram a valer no pré-filtro.
- **Contrato de saúde aceitava perder metade das disciplinas** (`< len/2`).
  Agora compara IDs; sumiu disciplina e nenhuma nova entrou, falha fechado.
  Virada de bimestre segue aceita.
- **Dedup de fase colapsava obrigações distintas** (chave por verbo). Entrega
  individual e de grupo, mesmo horário, viravam uma. Passa a usar o rótulo.
- **Teto de posts valia metade.** Os três seletores casavam o mesmo elemento e
  o corte vinha antes da desduplicação: 10 guardados eram 5 reais, em nove
  fóruns. Corrigido, e o truncamento agora aparece no log.
- **`item_aberto` tratava ausência de frase como prova de abertura.**
  "Submissões fechadas" e "o prazo de envio terminou" passavam como abertas.
  Página de login ou sem permissão devolve indefinido.
- **O aviso de coleta incompleta nunca chegava ao site nem ao e-mail**, porque
  `gerar_guia` retornava antes do render. A correção mais importante da rodada
  1 estava pela metade.

## Auditoria rodada 3 (25/07/2026)

Relatório em `AUDITORIA-INDEPENDENTE-RODADA-3-2026-07-25.md`. Sete achados,
sete reproduzidos, sete corrigidos. **Quatro caíram na mesma camada**: extração
de prazo de texto livre. Terceiro round seguido em que o conserto resolve o
caso relatado e abre o vizinho.

Por isso a mudança aqui não foi outro remendo de regex, foi **trocar o modo de
falhar**. Todo prazo lido de aviso agora carrega confiança:

- **alta** (dono e tipo inequívocos) → vira tarefa com data;
- **baixa** → vai pro bloco "Confirme se isto é prazo mesmo", com a frase
  original e o link do aviso.

Isso converte a pior falha (prazo inventado) na mais barata (prazo pedindo
conferência) e resolve como classe, não como caso. Corrigidos:

- assunto novo sem dois pontos ("LIVE MAGNA será realizada em 30/07") colava a
  data no módulo anterior. Título em caixa alta encerra o escopo; prosa corrida
  não, porque o aviso real descreve o Módulo 4 em várias linhas seguidas;
- subtítulo fora da lista de fases ("Grupo A:") deixava o prazo órfão;
- gatilho antes e depois da data discordando escondia o fechamento;
- **negação virava obrigação**: "Não haverá entrega em 30/07" criava entrega em
  30/07. Agora derruba o candidato;
- disciplina nova perdoava a perda de outra, e sem `id` a checagem se desligava
  calada;
- dedup cortava o rótulo em 60 caracteres e colapsava obrigações distintas;
- item que o robô não conseguiu abrir aparecia igual a um verificado.

Produto, decidido pelo Josemar: higiene do AVA saiu da fila principal (18
itens) para bloco recolhido; e-mail ganhou topo decisório e manteve a lista
completa embaixo; assunto diz a decisão, não a contagem.

## Auditoria rodada 4 (25/07/2026)

Relatório em `AUDITORIA-INDEPENDENTE-RODADA-4-2026-07-25.md`. Cinco achados
verificados: quatro procedem e foram corrigidos, um (colisão de identidade por
rótulo) não reproduzi como falha concreta mas a chave era frágil e foi trocada.

- **A saúde não olhava nenhuma fonte de prazo.** Com avisos, calendário e
  cronograma vazios ao mesmo tempo, a coleta terminava com zero prazo e
  `status: ok`. A proteção da rodada 1 cobria a estrutura e deixava passar o
  dado que dá sentido ao produto. Agora cada fonte é comparada com a leitura
  anterior: fonte que tinha conteúdo ontem e voltou vazia hoje derruba a coleta.
- **Frescor.** O site mandou refazer um quiz já concluído, porque o retrato era
  das 8h e ele estudou depois. Não era erro de parser. O robô passou a reler às
  8h, 11h, 14h, 17h e 20h, e a página avisa quando o retrato passa de 3 horas.
  O e-mail continua sendo um por dia, o da manhã.
- Falha de SMTP retornava 0 **e** o passo tinha `continue-on-error`: duas
  camadas transformando "o e-mail parou de chegar" em verde.
- O e-mail era enviado **antes** do push, então push quebrado deixava o aviso
  apontando pra um site velho. Publicar vem primeiro.
- O cronograma regular era aplicado como fallback até na COM170, que é
  quinzenal, e a telemetria dizia "cronograma: 4" quando eram 3.
- `data.json` e `estado.json` eram escritos direto; interrupção deixava arquivo
  pela metade e o `carregar()` tratava corrompido como ausente. Agora é
  temporário + substituição atômica.

**O e-mail diário é o heartbeat.** Não há monitor externo: se o e-mail das 8h
não chegar, o robô parou. Vale saber disso.

## Auditoria rodada 5 — fase imediata (25/07/2026)

Homologação adversarial das correções da rodada 4. Relatório em
`AUDITORIA-INDEPENDENTE-RODADA-5-IMEDIATA-2026-07-25.md`. Os casos vizinhos
foram reproduzidos e corrigidos:

- a primeira perda das fontes falhava fechado, mas gravava os zeros como nova
  referência; a segunda pane idêntica voltava a `ok`. Tentativa falha agora
  possui telemetria separada e a baseline continua sendo o último snapshot
  válido;
- fórum offline com posts em cache parecia fonte viva. A coleta agora distingue
  leitura ao vivo, cache, fonte parcial, degradada e falha;
- quedas grandes que não chegavam a zero passavam. Fonte que cai para menos da
  metade da última leitura válida falha fechado;
- `checked_at` era atualizado mesmo quando o conteúdo antigo era preservado.
  Agora existem `snapshot_at`, `attempted_at` e `publication_id`;
- o aviso de frescor era calculado só ao gerar HTML. JavaScript recalcula a
  idade a cada minuto e quando a aba volta ao primeiro plano;
- recado manual pode declarar `requires_pending_cmids` e `valid_until`; se a
  condição mudou, ele é arquivado automaticamente;
- Secret SMTP ausente agora é erro. Execução local sem e-mail exige
  `EMAIL_OPCIONAL=1`;
- a rodada das 8h ganhou um cron próprio, então atraso do runner não suprime o
  e-mail;
- push não é mais tratado como publicação: o workflow espera o mesmo
  `publication_id` aparecer no `data.json` servido pelo Pages antes do SMTP;
- JSON e HTML usam temporário único, `fsync` e substituição atômica. O cache é
  substituído antes e `data.json` funciona como marcador final do snapshot;
- identidade normaliza `cmid` para string e cai para URL ou seção+rótulo quando
  o Moodle não fornece ID;
- `testes/test_operacao.py` congela os cenários acima e roda na Action.

## Modularização e autoridade dos fóruns (25/07/2026)

Implementação concluída e validada no AVA real pela Action
[`30179941510`](https://github.com/esdraaline/mentor-univesp-com170/actions/runs/30179941510).
Todos os passos ficaram verdes: testes, coleta, publicação confirmada no Pages,
e-mail e saúde. O site público serviu o mesmo `publication_id` gerado pela
coleta.

O antigo `automacao/coletar.py`, com 1.741 linhas e quase todas as
responsabilidades, virou um ponto de entrada compatível de 98 linhas. O mapa
novo é:

```text
automacao/
  configuracao.py       caminhos, URLs, limites e fuso
  modelos.py            SourceResult e contratos JSON
  persistencia.py       cache versionado e escrita atômica
  saude.py              cobertura, idade e política de saúde
  pipeline.py           orquestra e combina fontes independentes
  dominio/
    datas.py            datas e normalização textual
    prazos.py           escopo, negação, confiança e casamento
    acoes.py            fila, urgência, dedup, identidade e novidades
    dependencias.py     cadeia real e prioridade herdada
  fontes/
    moodle.py           API, navegação e falhas operacionais tipadas
    disciplinas.py      descoberta, cursos, seções e status de conclusão
    calendario.py       API + DOM
    cronograma.py       cronograma oficial
    foruns.py           cache, autoridade, duas passagens e truncamento
    itens.py            aberto, fechado ou indefinido
    notificacoes.py     notificações e metadados de mensagens
  coletar.py            entrada fina e compatibilidade
```

Cada fonte publica em `fontes_status`: estado, última leitura ao vivo, idade,
quantidade, uso de cache, problemas e truncamento. Disciplina/estrutura é
obrigatória e continua falhando fechado. Calendário, cronograma e fóruns usam o
último resultado válido da própria fonte quando possível, sem impedir que as
demais sejam atualizadas. Erro operacional conhecido degrada a fonte; erro de
programação continua derrubando o job.

Nos fóruns:

- autores encontrados nos fóruns “Avisos” são acumulados por disciplina;
- Avisos e fóruns do grupo gastam o orçamento antes dos demais;
- desduplicação vem antes da ordenação e do corte;
- ordem interna: autor institucional, post com prazo, demais posts;
- post de colega com data continua coletado, mas sempre com confiança baixa;
- site e e-mail diferenciam visualmente “aviso oficial” e “post de colega”;
- telemetria registra quantos posts institucionais foram vistos e guardados.

Na primeira execução real, foram lidos 60 avisos: 20 institucionais e 40 de
colegas. O registro institucional encontrou autores nos quatro cursos
(`18870`: 1, `18880`: 3, `18893`: 1, `18922`: 3). As seis fontes terminaram
`live`; o truncamento de fóruns ficou explicitamente visível.

Testes novos:

- `testes/test_golden.py` e fixture sanitizada congelam ações, prazos, fontes e
  estados anteriores à migração;
- `testes/test_isolamento_fontes.py` prova falha isolada, preservação da
  descoberta obrigatória, propagação de erro inesperado e telemetria completa;
- `testes/test_foruns.py` cobre autoridade, duas passagens, corte após dedup,
  persistência entre leituras, baixa confiança de colega e apresentação nos
  dois canais.

## Risco aceito (decisão do Josemar, 25/07/2026)

O `docs/data.json` público contém nomes e trechos de posts de colegas (38
autores, 48 trechos na medição do dia). A auditoria classificou como crítico e
recomendou parar de publicar corpo e nome de aluno. **Josemar decidiu manter
como está.** Fica registrado para não ser "descoberto" de novo como bug: é
escolha consciente, não descuido. Se mudar de ideia, o ponto de corte é
`_preparar()` em `automacao/coletar.py` e `render_aviso()` em `render.py`.

## Auditoria completa e mapa do AVA (04/08/2026, à noite)

Varredura do código inteiro, módulo por módulo, e do AVA logado, disciplina por
disciplina, incluindo boletim, questionários, plano de ensino, cronograma
oficial e a ferramenta de participação. O que segue substitui as listas soltas
de pendência das auditorias anteriores.

### O achado que muda a prioridade de tudo

**COM100, S2 - Atividade Avaliativa: selo "Concluído" no AVA, zero tentativas,
nota em branco, prazo em 09/08.** A conclusão daquele item é por visualização.
O guia confia no selo (`status == "Concluído"` sai da fila) e nunca cobrou.

É a mesma classe do bug do Laboratório de Avaliação, agora sobre uma nota:
**o selo de conclusão do Moodle não prova entrega.** A prova está em dois
lugares que o robô não lê: a página do questionário ("Suas tentativas") e o
boletim.

Boletim na data da auditoria: COM100 S1 10,00 · S2 em branco · Média AVA 0,80.
LET110 S1 10,00 · S2 7,50 · Média 1,70. SOC100 com as duas feitas mas boletim
sem linhas (relatório do usuário vem vazio nessa disciplina). COM170 com
"Erro" na Média AVA e os cinco quizzes SCORM da Quinzena 1 marcados 0,00.

### Fontes do AVA que existem e o robô ignora

| Fonte | O que entrega | Onde |
|---|---|---|
| **Boletim** | nota por item, feedback escrito do facilitador, prova de que foi entregue | `/grade/report/user/index.php?id=<curso>` |
| **Tentativas do questionário** | "Suas tentativas" / "Situação: Finalizada" | página do próprio quiz |
| **Progresso de Participação** | placar oficial da COM170: 5 critérios por quinzena, perfil temporal, resultado por quinzena | `ativa.univesp.br/lti/progress` (LTI `cmid 220710`) |
| **cronograma.ics** | as mesmas datas do cronograma, em formato de calendário | `assets.univesp.br/cronograma/2026/` |
| **Prova presencial** | 60% da nota | `acesso.univesp.br`, autenticação própria |

Regra de participação da COM170, lida na ferramenta: cinco critérios de mesmo
peso por quinzena (conclusão dos Módulos 1, 2, 3 e 4 e "qualidade da
participação"), e a qualidade considera **a distribuição das interações ao
longo da quinzena**. Fazer tudo no último dia pontua menos. Situação na data:
Q1 com todos os critérios atendidos, Q2 "ainda não iniciada".

### Defeitos encontrados na auditoria de código

Por gravidade, com o arquivo onde cada um mora.

1. **Selo de conclusão aceito como prova de entrega** (`dominio/acoes.py`).
   Vale para quiz, scorm, assign e workshop. É o defeito acima.
2. **Boletim não é lido.** Sem ele não há como saber nota, feedback, nem
   confirmar entrega quando o selo mente.
3. **Participação da COM170 não é lida.** O sistema que decide a nota de
   participação está fora do retrato.
4. **Seção bloqueada não gera item** (`dominio/acoes.py`), então a cadeia de
   `dependencias.py` não tem alvo com prazo para propagar. É por isso que os
   dois SCORM da Q2 Módulo 1 aparecem "sem prazo" mesmo sendo eles que
   destravam o Módulo 4, que vence 09/08.
5. **Autor institucional só entra, nunca sai** (`fontes/foruns.py`). Um colega
   que poste uma vez num fórum "Avisos" vira fonte oficial permanente, e as
   datas dele passam a valer como confiança alta.
6. **Cronograma lido por posição** (`fontes/cronograma.py`): `datas[0]` início,
   `[1]` vencimento, `[2]` carência. `achar_datas` devolve em duas passadas
   (numérica antes da textual), então uma linha que misture "20/07" e "29 de
   julho" embaralha. Existe `.ics` publicado, que resolve por construção.
7. **`CRONOGRAMA_PADRAO` fixo no 3º bimestre de 2026** (`configuracao.py`).
   Na virada do bimestre o fallback passa a aplicar datas velhas em silêncio.
8. **`normalizar_estado` não invalida cache por versão** (`persistencia.py`):
   só preenche o campo. Quem invalida de verdade é o `schema_version` por
   discussão, em `foruns.py`. O mecanismo global é decorativo.
9. **Eventos sem nome no JSON público** (`fontes/calendario.py`): 42 eventos,
   12 com nome. Os outros 30 vêm da grade do mês sem descrição. Não viram ação,
   mas engordam o artefato e a contagem de saúde. Filtrar de uma vez derruba a
   coleta seguinte (a saúde reprova queda para menos da metade), então precisa
   ser feito junto com uma mudança no que a saúde conta.
10. **E-mail dispara em todo `workflow_dispatch`** (`guia-diario.yml`). Três
    rodadas manuais de verificação num dia viram três e-mails.
11. **Notificação não vira nada.** Existe feedback devolvido pelo facilitador
    na S2 da COM170 que nunca chegou ao guia.
12. **Artefato grande commitado cinco vezes por dia**: `data.json` 245 KB e
    `estado.json` 298 KB; `.git` em 6,9 MB com 160 commits. Ainda confortável,
    mas cresce sozinho.

## Plano de melhorias, em ordem

Cada etapa é fechada em si e tem como saber se deu certo.

### Etapa 1 — Provar entrega, não acreditar no selo · FEITA em 04/08/2026

`fontes/boletim.py` lê o relatório do usuário de cada disciplina. Cada linha
aponta para o `cmid` da atividade, então nota e devolutiva grudam no item certo
sem casar por nome. O item passa a carregar `nota`, `nota_txt`, `tem_nota` e
`feedback`.

`itens.entrega_feita()` é a segunda prova, aberta só onde o selo é suspeito
(vale nota, marcado "Concluído" e sem nota lançada): a página do questionário
diz "Suas tentativas / Situação: Finalizada" depois de respondido, e só o botão
"Tentativa do questionário" antes.

`acoes.entrega_provada()` decide com três provas — nota lançada (inclusive
0,00), devolutiva escrita, ou tentativa/envio confirmado. **"Concluído" só tira
da fila quando não houver prova em contrário.** `None` (não sei) nunca vira
acusação: só a conferência negativa mantém o item na fila, com o selo "sem
entrega registrada" e a explicação de que a conclusão daquele item fecha por
visualização.

Detalhes que custaram tempo e ficam registrados:

- a tabela de notas monta depois da página. Espera fixa fazia a leitura
  oscilar entre "tem nota" e "não tem"; agora espera pela primeira linha com
  link de atividade. Sem isso, a nota apareceria e sumiria entre rodadas;
- boletim vazio existe de verdade (SOC100 não mostra nenhuma linha) e é
  diferente de tabela que não renderizou. O primeiro é `vazio_confirmado`, o
  segundo é falha e usa cache;
- o boletim fica **fora** da lista que deixa a Action vermelha. Ele só
  acrescenta prova de entrega: sem ele o guia fica mais cauteloso, nunca menos.

*Aceite:* a S2 do COM100 aparece na fila com prazo 09/08 enquanto não for
respondida, e sai no instante em que a nota entrar.

### Etapa 2 — Nota e devolutiva à vista · FEITA em 04/08/2026

Aba "Como estou" (`render_notas`): nota por atividade, média por disciplina e a
devolutiva escrita do facilitador. A aba só existe quando há o que mostrar, e o
selo conta quantas atividades já têm nota.

Três estados diferentes, cada um com uma frase própria, porque significam
coisas opostas:

- **nota lançada**: mostra o valor;
- **sem nota lançada até agora**: vale nota e ainda não foi corrigida ou
  entregue, sem afirmar qual dos dois;
- **o AVA não registrou nenhuma entrega sua**: só quando a conferência da
  Etapa 1 provou a ausência. É a ponte entre as duas etapas.

Média com "Erro" (COM170) aparece como falha de cálculo do AVA, não como nota
zero e não como defeito do guia. Disciplina cujo boletim não lista atividade
(SOC100) aparece dizendo exatamente isso.

*Aceite:* a aba mostra 10,00 e 7,50 do LET110, a média 0,80 do COM100, o "Erro"
da COM170 explicado, o elogio do facilitador na S2 - Ferramenta para Envio, e a
S2 do COM100 marcada como sem entrega registrada.

### Etapa 3 — Participação da COM170 · FEITA em 04/08/2026

`fontes/participacao.py`. O item "Meu Progresso de Participação" é um
lançamento LTI: navegar até ele **abre uma aba nova** em `ativa.univesp.br`, e
a leitura precisa capturar a página que nasce (`context.expect_page`), não a
que foi navegada. Se nenhuma aba nascer, procura entre as já abertas antes de
desistir.

Publica por disciplina: resultado da quinzena corrente, perfil temporal,
critérios um a um com a situação, e o panorama das sete quinzenas. A aba "Como
estou" mostra isso acima das notas.

O perfil temporal ganhou frase explicando o que ele mede, porque é a régua
menos óbvia: a ferramenta considera **como as interações se distribuem na
quinzena**, então entregar tudo no último dia pontua menos mesmo entregando
tudo.

Como o boletim, participação **não bloqueia a publicação**: é fonte que
acrescenta leitura, e sua ausência não esconde prazo.

*Aceite:* o guia mostra "Q1 - Resultado final · Progresso muito avançado",
perfil temporal "No prazo", os critérios atendidos e o panorama Q1 a Q7.

### Etapa 4 — Prazo herdado por quem destrava · FEITA em 04/08/2026

O plano original não sobrevivia ao contato com o AVA: **seção bloqueada não
traz item nenhum** (o Moodle não renderiza o conteúdo de seção travada), então
não havia o que gerar. O alvo com prazo tinha que vir de outro lugar.

Veio da tabela. A página de instruções da quinzena tem um calendário com
legenda ("Calendário da Quinzena 2, de 3 a 18 de agosto de 2026") e células
marcadas por classe: `prazo` no fechamento, `estudo`/`entrega`/`leitura` nas
etapas. Isso é **estrutura, não prosa**: o dia vem do número da célula, o mês e
o ano vêm da legenda, o rótulo vem escrito ("PRAZO MÓDULO 4"). Por isso estes
prazos nascem com **confiança alta**, ao contrário do resto de
`fontes/instrucoes.py`, que continua indo para "confirme se é prazo".

Três defeitos apareceram no caminho, todos de identidade de seção:

1. **`FAMILIA_RE` não casa título prefixado.** "Q2 Módulo 4" começa por
   dígito depois do Q, e o padrão exige começar por não-dígito. O prefixo
   passa a ser removido antes da comparação.
2. **"Módulo 4" existe em toda quinzena.** Sem qualificar, o prazo de 09/08
   grudou no Módulo 4 da Quinzena 1, que encerrou. O escopo vindo da tabela
   carrega `quinzena`, e a regra ficou estrita nos dois sentidos: escopo com
   quinzena só cobre seção daquela quinzena, e escopo sem quinzena (avisos
   antigos) não invade a quinzena nova. Sem a segunda metade, o aviso sobre
   "Módulo 6 e 7" da Quinzena 1 passou a cobrar o Q2 Módulo 6, que sequer
   abriu.
3. **A cadeia de desbloqueio lia o marcador errado.** "Q2 M3 - Alucinação"
   tem dois marcadores, e `secao_do_predecessor` pegava o primeiro: entendia
   "quinzena 2" onde devia entender "módulo 3", e a cadeia parava no lugar
   errado. Agora o módulo vem do último marcador e o primeiro diz em qual
   quinzena procurar.

*Aceite, verificado com os dados reais:* "Q2 M1 - Atividade: tokenizador
interativo" saiu de "sem prazo" e passou a exibir "faça antes de 09/08, é ele
que destrava o Q2 Módulo 4". O Módulo 4 aparece como alerta bloqueado com a
data. Nenhuma linha nova apareceu para a Quinzena 1.

### Etapa 5 — Endurecer as fontes frágeis · FEITA em 04/08/2026

**Autor institucional com validade.** O registro só crescia: quem postasse uma
vez num fórum "Avisos" virava fonte oficial para sempre, e as datas dessa
pessoa passavam a valer com confiança alta. Agora guarda-se **quando** cada
autor foi visto, e quem some por mais de `VALIDADE_AUTOR_DIAS` (90) deixa de
ser fonte. Formato antigo (lista) é convertido na leitura, sem perder o que já
havia.

**Cronograma de reserva não fica preso a um bimestre.** A URL estava fixa em
`cronograma_regular_3.html`. Na virada do bimestre a reserva aplicaria um
calendário inteiro de datas vencidas, em silêncio. Agora sai da data corrente.

Só que derivar bimestre de mês é palpite, e palpite que acerta uma página
válida com datas erradas é pior que erro visível. Então **quem lê o cronograma
confere se as semanas cercam a data de hoje** (com 30 dias de margem) e
descarta o que não cobre. Vale para qualquer cronograma, inclusive o que a
disciplina publica: se ela linkar um cronograma velho, isso aparece.

**Eventos sem nome saíram do artefato.** A grade do mês devolve `data-event-id`
que a lista de próximos eventos não descreve: eram 30 de 42 registros sem nome,
sem URL e sem atividade. Não viravam ação, só engordavam o JSON público.

A limpeza esbarrou na própria saúde: ela reprova fonte que cai para menos da
metade da leitura anterior, então cortar 30 de 42 faria a rodada seguinte
falhar fechado sem motivo real. A checagem passou a usar `eventos_uteis`
(eventos com nome), chave nova e sem histórico, que fica sem baseline na
primeira rodada e protege a partir da segunda.

*Aceite:* suíte verde, incluindo o teste dourado com a chave nova congelada.

### Etapa 6 — Prova presencial · PARCIAL em 04/08/2026

**Feito: a lacuna deixou de ser invisível.** `dominio/avaliacao.py` lê a
composição da nota de aviso institucional já coletado, e a aba "Como estou"
passa a mostrar, por disciplina, "40% AVA · 60% prova presencial" com a frase
que faltava: *este guia acompanha só a parte do AVA; a data e o local saem no
Sistema de Provas, que tem login separado*.

Isso importa mais do que parece. Sem a linha, "está tudo em dia" soava como
"está tudo em dia na disciplina", quando o robô só enxerga a menor metade.

A regra não é chutada: só aparece quando **um mesmo aviso oficial declara os
dois percentuais e eles somam 100**. Percentual solto não vira afirmação sobre
a nota inteira, e post de colega não define regra de avaliação. Foi lida com
sucesso nas duas redações que existem no AVA hoje ("40% - nota pela
participação na fase de estudos (AVA)" no COM100, e "40% atividades
avaliativas do AVA mais 60% da prova final" no LET110).

**Não feito: a data da prova.** Continua fora do alcance, em
`acesso.univesp.br`, com autenticação própria. O coletor exige decidir onde
guardar mais uma credencial, e essa decisão é do Josemar. Enquanto isso o guia
declara a ausência em vez de omiti-la.

Quando for feito, o caminho já mapeado: o calendário do AVA não lista prova
para estas disciplinas, e nenhum aviso trouxe data até agora, então a fonte
tem mesmo que ser o Sistema de Provas.

### Manutenção que não é código

- **Conferência quinzenal contra o AVA.** Os nove defeitos de 04/08 só
  apareceram porque alguém comparou o site com o AVA na mão. A virada de
  quinzena (16/08) é o momento de maior risco.
- **Rodar a Action às 8h sem intervenção** e confirmar que o e-mail chega. O
  e-mail é o único batimento cardíaco do sistema.

## Pendências do Josemar

- **Responder a S2 - Atividade Avaliativa do COM100.** Vence 05/08 pelo
  cronograma, com carência até 09/08. Não tinha nenhuma tentativa em 04/08.
- Apagar o Secret `AVA_STORAGE_STATE`, obsoleto desde 25/07.

Sobre a senha exposta no histórico do repositório (seção de segurança acima):
**Josemar decidiu não tratar** (04/08/2026). Fica só como registro, não é
pendência, e não deve voltar como cobrança em sessão futura.
- Revisão semanal da mentora continua manual: escrever `docs/revisao.json` e
  rodar `python automacao/gerar_guia.py --render-only`.

## Decisões que valem lembrar

- **Suíte verde não é prova de que funciona.** Em 04/08/2026 três defeitos
  passaram por todos os testes e falharam no AVA: o selo do Moodle aceito como
  entrega, a tabela de notas que monta depois da página, e o texto de aviso
  cortado em 400 caracteres. Nos três casos o teste usava um dado gentil que eu
  mesmo escrevi. Quando um teste cobre leitura do AVA, o corpo dele tem que ser
  o texto real, copiado da página, com truncamento e quebras e tudo.
- **Rodar contra o AVA de verdade e conferir a saída** é o único passo que pegou
  esses três. Vale especialmente na virada de quinzena e de bimestre.
- **Prazo nunca é estimado.** Foi o erro original e não deve voltar.
- **Item fechado sai da fila** e vai pro bloco recolhido "já encerrou".
- **Seção bloqueada com prazo vira alerta**, senão o item mais urgente ficaria
  invisível justo por estar travado.
- **A urgência sobe pela cadeia de módulos:** o que destrava a etapa com prazo
  herda o prazo dela.
- **O site é público**, então mensagem privada entra só como metadado (sem
  conteúdo) e post de fórum entra truncado, com link pro original.
