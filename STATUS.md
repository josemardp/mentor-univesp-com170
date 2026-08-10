# STATUS — Guia diário do AVA (mentor-univesp)

> Doc de handoff. Qualquer máquina ou agente retoma a partir daqui.
> Site: https://esdraaline.github.io/mentor-univesp-com170/ (conta GitHub `esdraaline`)
> Histórico completo de sessões, auditorias e etapas concluídas: [`docs/HISTORICO.md`](docs/HISTORICO.md)

## Estado atual (10/08/2026)

Funcionando e verificado na nuvem. O robô roda sozinho em cinco janelas do dia (8h de Brasília com site + e-mail; 11h, 14h, 17h e 20h só o site), entra no AVA, lê as 8 fontes (`disciplinas`, `itens`, `calendario`, `cronograma`, `foruns`, `notificacoes`, `boletim`, `participacao`), monta a agenda e manda o resumo por e-mail.

**Fechado em 10/08:** o boletim vazio do SOC100 é estado real do AVA (conferido ao vivo: a página do relatório de notas só tem cabeçalho). Duas correções saíram disso: (1) disciplina com boletim lido não some mais da aba "Como estou", e a mensagem distingue "li e está vazio" de "não consegui ler"; (2) **nota que sai virou notícia** — a aba "Chegou novo" e o e-mail passam a anunciar nota lançada ou corrigida, com a devolutiva do facilitador junto. Antes disso a nota só existia na aba "Como estou", sem nada dizer que ela tinha acabado de aparecer.

Prazos vêm de três fontes e a origem de cada data aparece no site: calendário do AVA, cronograma oficial e avisos de facilitador (com link pro post). **Nenhuma data é estimada** — sem fonte oficial, o site diz que não há prazo.

Secrets no repo `esdraaline/mentor-univesp-com170`: `AVA_USUARIO`, `AVA_SENHA`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_PARA`. Nenhuma credencial versionada (o repositório é público).

## Próximo passo

**Data da prova presencial** — única lacuna funcional aberta. Fica em `acesso.univesp.br`, com autenticação própria. Depende de uma decisão do Josemar: onde guardar mais uma credencial. Enquanto isso, o guia declara a ausência em vez de omiti-la ("40% AVA · 60% prova presencial", com aviso de que o guia só acompanha a parte do AVA).

## Auditoria ao vivo (08/08/2026, 23:37 UTC)

Conferido item por item nos quatro cursos (COM100, SOC100, LET110, COM170), entrando em cada atividade avaliativa em vez de confiar só no rótulo "Concluído" (esse rótulo do Moodle às vezes marca por visualização, não por envio).

O **COM170 avançou para uma estrutura nova**: além das 4 Semanas do AIA, agora tem "Quinzena 1" e "Quinzena 2", com módulos que se destravam em sequência. Essa estrutura ainda não está mapeada nas referências da skill mentor-univesp (que são um retrato de 02/07/2026).

## Pendências do Josemar

- ~~Responder a S2 - Atividade Avaliativa do COM100~~ feito em 08/08, nota 10,00/10,00 (confirmado ao vivo).
- ~~COM170, Quinzena 2: concluir o Módulo 4 até 09/08~~ feito. Em 10/08 os módulos M1 a M4 estão concluídos com nota lançada no boletim (prova de entrega, não só selo do Moodle). O que segue é o **Laboratório de Avaliação**: envio até **15/08 23:59** e revisão entre pares até **18/08 23:59** (prazo do calendário do AVA, campo `closesubmission`/`closeassessment`, não presumido). No AVA os itens abertos da quinzena são "Q2 M5 - Caso B", "Q2 M6 - Tutorial/Revisão entre pares" e "Q2 M7 - Grupo/Revisão entre pares".
- Responder a **S3 - Atividade Avaliativa do COM100** (abriu 03/08, fecha domingo 16/08 23:59; sem tentativa, sem urgência ainda).
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
- **Silêncio não é resposta.** Boletim vazio, leitura que falhou e "não entregou" levam a decisões diferentes e não podem sair com a mesma frase — nem sumir da tela, que foi o que o SOC100 fazia até 10/08.
- **Nota nova se apoia no retrato anterior, nunca no cache.** Leitura de boletim que falha devolve nota do cache; comparar contra ela anunciaria como nova uma nota velha. Disciplina sem leitura boa na rodada anterior fica de fora até haver duas seguidas. A notícia vale por `NOVO_ATE_DIAS` (3), porque o robô roda 5 vezes ao dia e ele lê o guia uma.
- **Prazo de módulo trancado não aparece na página do módulo, aparece na página de instruções da quinzena/semana.** Auditoria de 08/08 checou a atividade do Módulo 1 e concluiu "sem prazo visível", mas o prazo do Módulo 4 estava na página "Instruções da Quinzena" (id=215566), não na atividade em si. Conferir sempre a página de instruções/calendário da unidade inteira, não só os itens travados.
