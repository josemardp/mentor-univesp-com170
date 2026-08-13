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

**Residual conhecido:** isso cobre rodada que roda e falha. Não cobre rodada que *nunca dispara* (cron que não fira, workflow desabilitado). Para isso só um vigia fora deste repositório resolveria.

## Próximo passo

**Data da prova presencial** — única lacuna funcional aberta. Fica em `acesso.univesp.br`, com autenticação própria. Depende de uma decisão do Josemar: onde guardar mais uma credencial. Enquanto isso, o guia declara a ausência em vez de omiti-la ("40% AVA · 60% prova presencial", com aviso de que o guia só acompanha a parte do AVA).

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
- **COM170, Quinzena 2: enviar os dois portfólios até 15/08 23:59.** Confirmado ao vivo em 13/08 que nenhum dos dois foi enviado. A avaliação entre pares vai de 16 a 18/08 23:59 e vale ponto separado. Antes disso ainda estão abertos o "Q2 M5 - Caso B" e o tutorial do M6. Os templates estão no "Q2 M5 - Templates".
- **Puxar a conversa do G4.** O espaço do grupo está vazio e ninguém combinou representante. Pelas instruções da quinzena, o grupo funciona com dois ou com cinco, e quem chega primeiro deve começar assim mesmo.
- **Responder S3 de COM100, LET110 e SOC100 até 16/08 23:59** e **S4 das três até 23/08 23:59**. Nenhuma das seis tem tentativa registrada (conferido no AVA, não no selo).
- **Perguntar ao facilitador do COM170** por que a Quinzena 1 está com 0,00 nos dois envios, e ao SOC100 por que o boletim não lista nenhum item.
- Regularizar o **S1 - Formulário de conhecimentos prévios do COM170** (segue pendente, mesmo caso desde julho: falar com SAE ou orientador de polo).
- Apagar o Secret `AVA_STORAGE_STATE`, obsoleto desde 25/07.
- Revisão semanal da mentora, ainda manual: escrever `docs/revisao.json` e rodar `python automacao/gerar_guia.py --render-only`.

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
- **Prazo de módulo trancado não aparece na página do módulo, aparece na página de instruções da quinzena/semana.** Auditoria de 08/08 checou a atividade do Módulo 1 e concluiu "sem prazo visível", mas o prazo do Módulo 4 estava na página "Instruções da Quinzena" (id=215566), não na atividade em si. Conferir sempre a página de instruções/calendário da unidade inteira, não só os itens travados.
