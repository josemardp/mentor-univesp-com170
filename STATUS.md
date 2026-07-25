# STATUS — Guia diário do AVA (mentor-univesp)

> Doc de handoff. Qualquer máquina ou agente retoma a partir daqui.
> Site: https://esdraaline.github.io/mentor-univesp-com170/ (conta GitHub `esdraaline`)

## Última sessão: 25/07/2026

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

## Próximo passo

- Conferir se a execução automática das 8h roda limpa. Todas as execuções de
  25/07 foram disparadas à mão (`workflow_dispatch`); o caminho do agendador
  ainda não foi exercitado com o código novo.

## Pendências

- **Josemar (estudo):** quiz "Identifique o paradigma" do Módulo 1 do COM170.
  É ele que destrava o Módulo 4, que vence 26/07 às 23:59.
- **Josemar (limpeza):** o Secret `AVA_STORAGE_STATE` ficou obsoleto (era o
  cookie de sessão do sistema antigo). Pode apagar sem risco.
- Revisão semanal da mentora continua manual: escrever `docs/revisao.json` e
  rodar `python automacao/gerar_guia.py --render-only`.
- 19 itens caem em "sem prazo definido". Ainda não é ruído, mas se crescer vale
  agrupar por disciplina ou recolher.
- As sub-seções do AIA no COM170 não são lidas (ficam atrás de uma página
  separada). Sem impacto: o AIA encerrou em 20/07.

Das auditorias, ainda não feito (ordem sugerida):

- **Prova presencial não é rastreada**, e vale 60% da nota. A rodada 2 apurou:
  o calendário público ainda não lista as 4 disciplinas atuais, e a fonte que
  prevalece é o Sistema de Prova (`acesso.univesp.br`), que pede autenticação
  própria, separada do AVA. Precisa de coletor à parte.
- **O filtro de fórum é permissivo demais.** Com o truncamento agora visível,
  dá pra medir: um fórum acusou 250 posts "relevantes" e outro 353, quando os
  avisos oficiais são poucos. Falta priorizar autor institucional em vez de
  palavra-chave genérica.
- Calendário: sem paginação (teto de 50) e o DOM só entra se a API vier vazia,
  em vez de somar as duas fontes.
- `item_aberto()` abre a página do quiz, que mostra "Aberto", "Fecha",
  tentativas e estado de envio, e só procura frase de encerramento.
- Sem retry/backoff e sem alerta externo se o cron não rodar.
- Notificação de feedback devolvido não vira ação; boletim não é lido (a
  COM170 segue com "Erro no cálculo do item de nota Média AVA").
- Cache sem versão de esquema: post guardado por um extrator antigo continua
  com o formato velho até a discussão receber post novo.

## Decisões que valem lembrar

- **Prazo nunca é estimado.** Foi o erro original e não deve voltar.
- **Item fechado sai da fila** e vai pro bloco recolhido "já encerrou".
- **Seção bloqueada com prazo vira alerta**, senão o item mais urgente ficaria
  invisível justo por estar travado.
- **A urgência sobe pela cadeia de módulos:** o que destrava a etapa com prazo
  herda o prazo dela.
- **O site é público**, então mensagem privada entra só como metadado (sem
  conteúdo) e post de fórum entra truncado, com link pro original.
