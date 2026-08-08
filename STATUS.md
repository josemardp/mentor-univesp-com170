# STATUS — Guia diário do AVA (mentor-univesp)

> Doc de handoff. Qualquer máquina ou agente retoma a partir daqui.
> Site: https://esdraaline.github.io/mentor-univesp-com170/ (conta GitHub `esdraaline`)
> Histórico completo de sessões, auditorias e etapas concluídas: [`docs/HISTORICO.md`](docs/HISTORICO.md)

## Estado atual (08/08/2026)

Funcionando e verificado na nuvem. O robô roda todo dia às 8h, entra no AVA sozinho, lê as 6 fontes, monta a agenda e manda o resumo por e-mail.

Prazos vêm de três fontes e a origem de cada data aparece no site: calendário do AVA, cronograma oficial e avisos de facilitador (com link pro post). **Nenhuma data é estimada** — sem fonte oficial, o site diz que não há prazo.

Secrets no repo `esdraaline/mentor-univesp-com170`: `AVA_USUARIO`, `AVA_SENHA`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_PARA`. Nenhuma credencial versionada (o repositório é público).

## Próximo passo

**Data da prova presencial** — única lacuna funcional aberta. Fica em `acesso.univesp.br`, com autenticação própria. Depende de uma decisão do Josemar: onde guardar mais uma credencial. Enquanto isso, o guia declara a ausência em vez de omiti-la ("40% AVA · 60% prova presencial", com aviso de que o guia só acompanha a parte do AVA).

## Auditoria ao vivo (08/08/2026, 23:37 UTC)

Conferido item por item nos quatro cursos (COM100, SOC100, LET110, COM170), entrando em cada atividade avaliativa em vez de confiar só no rótulo "Concluído" (esse rótulo do Moodle às vezes marca por visualização, não por envio).

O **COM170 avançou para uma estrutura nova**: além das 4 Semanas do AIA, agora tem "Quinzena 1" e "Quinzena 2", com módulos que se destravam em sequência. Essa estrutura ainda não está mapeada nas referências da skill mentor-univesp (que são um retrato de 02/07/2026).

## Pendências do Josemar

- ~~Responder a S2 - Atividade Avaliativa do COM100~~ feito em 08/08, nota 10,00/10,00 (confirmado ao vivo).
- Responder a **S3 - Atividade Avaliativa do COM100** (abriu 03/08, fecha domingo 16/08 23:59; sem tentativa, sem urgência ainda).
- Fazer as duas atividades do **COM170, Quinzena 2, Módulo 1** ("Atividade: tokenizador interativo" e "Atividade de embeddings: Mapa dos significados"): travam o acesso aos Módulos 2 a 6 da quinzena.
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
