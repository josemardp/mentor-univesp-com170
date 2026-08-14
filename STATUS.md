# STATUS — Guia diário do AVA (mentor-univesp)

> Doc de handoff. Qualquer máquina ou agente retoma a partir daqui.
> Site: https://esdraaline.github.io/mentor-univesp-com170/ (conta GitHub `esdraaline`)
> Histórico completo de sessões, auditorias e etapas concluídas: [`docs/HISTORICO.md`](docs/HISTORICO.md)

## Estado atual (13/08/2026)

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

## Próximo passo

**Pesos das semanas.** O aviso "Pesos das Atividades" diz que as avaliativas não valem igual: S1 8%, S2 12%, S3 a S6 17% cada, S7 12%. O guia trata todas como iguais, então a S3 (17%) aparece com o mesmo peso visual da S1 (8%). O aviso já chega ao robô desde a correção de 13/08; falta usar o número no cartão da atividade.

**Data da prova presencial** — segue sem fonte alcançável, mas não por falta de tentativa. Levantado em 13/08: o `acesso.univesp.br` autentica por conta Microsoft (`msal-browser.js`), fluxo diferente do SSO do AVA e provavelmente com MFA; a data não aparece em nenhum aviso, evento de calendário ou página de instrução coletada; o cronograma público não a traz; e o `cronograma.ics` que a própria Univesp linka responde **404**. O que passou a existir: o guia **procura** a data nos avisos oficiais e a mostra assim que um facilitador disser, exigindo "prova" e "presencial/polo" na mesma frase para não confundir com atividade avaliativa do AVA. Automatizar o login Microsoft continua fora de escopo por conta própria — é decisão do Josemar, e mexer com conta institucional pode disparar bloqueio de segurança.

## Auditoria ao vivo (14/08/2026, 18:10)

Conferência pontual pedida pelo Josemar, entrando nas páginas com a sessão dele. O que mudou desde 13/08:

- **Q2 M6 (individual) entregue** em 13/08 às 20:04. A auditoria de 13/08 pegou o estado anterior ao envio.
- **Q2 M7 (grupo) sem envio na conta dele**, com o colega tendo assumido a representação em 14/08 às 14:08. Estado esperado, mas não é prova de que o grupo entregou: o laboratório mostra o envio de cada aluno, então da conta do Josemar não dá para ver o do representante.
- **Ponto de encontro do G4 deixou de estar vazio.** Um tópico, aberto pelo facilitador em 13/08 às 17:42, com resposta do Josemar (13/08, 20:25) e do colega (14/08, 14:08).
- **As seis avaliativas S3/S4 continuam sem tentativa.** S3 fecha 16/08 23:59, S4 fecha 23/08 23:59 no AVA.
- **Quatro fóruns temáticos parados foram respondidos em 14/08**, entre 18:29 e 18:34, com texto aprovado por ele antes do envio: SOC100 S3 e S4, LET110 S3 e S4. Confirmado na página de publicações dele em cada curso, não pelo selo do Moodle.
- **COM100 S3 e S4 continuam parados e não dá para destravar por texto.** Os dois fóruns exigem o link de um projeto do próprio aluno no Scratch (S3 animação com repetição, S4 condicional mais variável mais entrada do usuário). Sem o desafio feito, não há o que postar.

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
- **COM170, Q2 M7 (portfólio em grupo): pedir ao colega o print do envio.** Ele assumiu a representação da quinzena, postou o template completo no ponto de encontro às 14:08 de 14/08 e avisou no WhatsApp do grupo às 14:19 que enviou ("Enviado! Confirmem depois se der se aparece aí ok"). **A conta do Josemar não tem como confirmar isso durante a fase de envio**: o laboratório mostra só o envio do próprio aluno, e a página dele diz "Você não enviou seu trabalho ainda", que é o estado esperado de quem não é o representante. Conferido às 18:15 de 14/08, quatro horas depois do aviso dele, e nada mudou nessa página — o que não é sinal de problema, é o desenho do Moodle. A confirmação barata é o print do bloco "Seu envio" na tela do colega, com título e horário. Sem isso, a certeza só vem em 16/08, quando abre a fase de avaliação.
- ~~Escrever no ponto de encontro do G4~~ **feito** em 13/08 às 20:25: ele listou os participantes (colega, colega, colega e ele), abriu a partilha com o caso B e perguntou quem pegaria a representação desta quinzena. O colega respondeu em 14/08. colega e colega não escreveram no fórum, mas constam como integrantes no template do grupo.
- **Avaliação entre pares do M6 e do M7, de 16 a 18/08 23:59.** Vale ponto separado da entrega e é a única etapa que segue depois do fim da quinzena.
- **Responder S3 de COM100, LET110 e SOC100 até 16/08 23:59** e **S4 das três até 23/08 23:59** (esta é a data de fechamento no AVA; o cronograma oficial diz 19/08). Conferido ao vivo em 14/08: **nenhuma das seis tem uma única tentativa** — as seis páginas mostram só o botão de iniciar, sem tabela de tentativas.
- **Fazer os dois desafios do Scratch do COM100** e postar o link nos fóruns temáticos S3 e S4. É o único jeito de destravar esses dois: o fórum pede o projeto do próprio aluno, não opinião. Os outros quatro fóruns temáticos parados (SOC100 S3/S4 e LET110 S3/S4) foram respondidos em 14/08.
- **Perguntar ao facilitador do COM170** por que a Quinzena 1 está com 0,00 nos dois envios, e ao SOC100 por que o boletim não lista nenhum item.
- Regularizar o **S1 - Formulário de conhecimentos prévios do COM170** (segue pendente, mesmo caso desde julho: falar com SAE ou orientador de polo).
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
- **Prazo de módulo trancado não aparece na página do módulo, aparece na página de instruções da quinzena/semana.** Auditoria de 08/08 checou a atividade do Módulo 1 e concluiu "sem prazo visível", mas o prazo do Módulo 4 estava na página "Instruções da Quinzena" (id=215566), não na atividade em si. Conferir sempre a página de instruções/calendário da unidade inteira, não só os itens travados.
