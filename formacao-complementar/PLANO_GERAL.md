# Plano geral

> Criado em 13/09/2026. Revisar a cada 4 módulos.

## 1. Objetivo

Concorrer a uma vaga de trabalho em IA **sem depender de IA** no teste técnico
e na entrevista.

Isso não significa parar de usar IA. Significa que, quando ela for desligada,
o que sobra precisa ser suficiente.

## 2. Decisões tomadas em 13/09/2026

| Decisão | Escolha | Motivo |
|---|---|---|
| Cloud do laboratório | **AWS free tier** | É o nome que aparece em descrição de vaga e em entrevista. Oracle Cloud tem free tier melhor, mas quase ninguém pergunta sobre ela |
| Ordem dos frameworks | **LangChain/LangGraph antes de n8n** | n8n esconde o mecanismo. O objetivo é entender o que o framework abstrai, então o mecanismo vem primeiro |
| Versionamento do curso | **Repositório git local, privado** | Regra fixa: repo nasce privado. Não foi criado no GitHub ainda |
| Velocidade | **Padrão, 8 a 10h por semana** | Compatível com trabalho de dia, família, estudo à noite e fim de semana |
| Vaga-alvo | **Não definida** | Sem vaga colada, sigo a ordem padrão. Ver seção 6 |

## 3. Ordem de aprendizagem ajustada

A ordem numérica das pastas (00 a 29) é o **índice**, não o **roteiro**. O roteiro abaixo
foi ajustado ao seu diagnóstico real.

### Fase 1: firmar o chão (módulos 00, 01, 04, 03)

**Por que primeiro:** você opera na camada alta sem a camada baixa firme. Isso aguenta
enquanto a IA está do lado e cede no teste técnico.

| Ordem | Módulo | Por que aqui | Estimativa |
|---|---|---|---|
| 1 | 00 Fundamentos (diagnóstico) | Sem medir, o resto é chute | 2h |
| 2 | 01 Python | Sua linguagem mais forte e a mais usada em IA. Firmar aqui dá alavanca em tudo | 3 semanas |
| 3 | 04 Git e GitHub | **Você não tem evidência de branch, merge ou conflito.** É eliminatório em processo seletivo e leva pouco tempo | 1 semana |
| 4 | 03 Linux e terminal | Suficiente para não travar. Não vira especialidade | 1 semana |

### Fase 2: backend de verdade (módulos 05, 06, 08)

**Por que aqui:** FastAPI é sua maior lacuna de alto retorno. E não dá para aprender API
sem HTTP firme antes.

| Ordem | Módulo | Por que aqui | Estimativa |
|---|---|---|---|
| 5 | 05 HTTP, REST, APIs | Base de tudo que vem depois. Seu código já usa Bearer e CORS sem você ter estudado | 2 semanas |
| 6 | 06 Bancos de dados | Você tem 94 migrations. Falta a teoria por baixo (índice, normalização, transação) | 2 semanas |
| 7 | 08 Backend FastAPI | Lacuna zerada. Vira projeto integrador 1 | 3 semanas |

### Fase 3: a camada que você já usa mas não domina (módulos 10, 11, 12, 13)

**Por que aqui:** aqui o curso para de ensinar coisa nova e passa a **destravar coisa que
já roda nos seus projetos**. É a fase de melhor custo-benefício do plano inteiro.

| Ordem | Módulo | Estudo de caso real | Estimativa |
|---|---|---|---|
| 8 | 10 IA generativa | `financeiroje/supabase/functions/ai-advisor/` | 1 semana |
| 9 | 11 Prompt engineering | `aiAdvisor/promptSanitizer.ts` e `systemPrompt.ts` | 2 semanas |
| 10 | 12 Embeddings | `secretario-task/supabase/migrations/0002_pgvector_intelligence.sql` | 2 semanas |
| 11 | 13 Vector database | O mesmo arquivo, agora olhando índice e performance | 1 semana |

### Fase 4: o que a vaga pede e você não tem (módulos 14, 15, 16)

**Por que aqui:** é o coração da vaga de IA. Só faz sentido depois da fase 3.

| Ordem | Módulo | Regra | Estimativa |
|---|---|---|---|
| 12 | 14 RAG | **Do zero antes de framework.** Sem exceção | 3 semanas |
| 13 | 15 Function calling | O assunto mais perguntado em entrevista de IA hoje | 2 semanas |
| 14 | 16 Agentes de IA | **Sem framework primeiro**, depois reconstruir com framework | 3 semanas |

### Fase 5: frameworks e escala (módulos 19, 20, 17, 18, 21, 22, 23, 24)

Só aqui entram LangChain, LangGraph, multiagentes, MCP, CrewAI, n8n, Flowise, OpenClaw.
Nesta ordem. O critério é: você já sabe fazer à mão, agora vê o que o framework economiza.

Estimativa: 8 semanas.

### Fase 6: profissionalizar (módulos 25, 26, 09, 07, 02)

Segurança, testes, observabilidade, cloud, frontend, JS/TS. Estimativa: 6 semanas.

### Fase 7: fechar (módulos 27, 28, 29)

Projetos integradores, entrevista, revisão final. Estimativa: 6 semanas.

### Deixado para o fim, de propósito

- **Módulo 21 CrewAI, 23 Flowise, 24 OpenClaw**: conhecer para citar, não para dominar
- **Java**: nota meta 1. Não compensa o tempo para vaga de IA
- **Módulo 02 JavaScript/TypeScript** só na fase 6: você já produz TS que funciona. Melhorar
  isso rende menos que zerar function calling

## 4. Duração total

| Velocidade | Horas por semana | Duração estimada |
|---|---|---|
| Leve | 5h | ~68 semanas (16 meses) |
| **Padrão (escolhida)** | **8 a 10h** | **~37 semanas (8 a 9 meses)** |
| Intensivo | 15h | ~23 semanas (5 a 6 meses) |

Marco intermediário importante: ao fim da **Fase 4 (semana ~22, por volta de fevereiro de 2027)**
você já tem conversa de entrevista de IA. Não precisa esperar a semana 37 para começar a se candidatar.

## 5. Regra de avanço

Só passa de módulo quando conseguir, **com IA desligada**:

1. Explicar o conceito em voz alta, sem material na frente
2. Implementar uma versão simples do zero
3. Ler código existente e dizer o que faz
4. Corrigir um bug plantado
5. Explicar o trade-off da escolha
6. Responder a pergunta de entrevista do módulo

Falhou em qualquer um: não avança. Nota no mapa fica abaixo de 4.

## 6. Onde a vaga-alvo mudaria tudo isto

Você não colou vaga nenhuma, então este plano é o genérico para "vaga de IA no Brasil, 2026".
Registrando o que mudaria, para quando você colar:

| Se a vaga for de... | O que sobe | O que desce |
|---|---|---|
| **Engenharia de IA / LLM** | 14 RAG, 15 Function calling, 16 Agentes, 20 LangGraph para o início | 07 React, 02 JS/TS |
| **Automação / RPA** | 22 n8n sobe para a Fase 2, junto com 05 APIs | 12 Embeddings, 13 Vector DB, 20 LangGraph |
| **Full stack com IA** | 08 FastAPI e 07 React sobem | 17 Multiagentes, 21 CrewAI |
| **Dados / analytics** | 06 Bancos de dados vira fase 1, entra SQL avançado | 16 Agentes, 18 MCP |
| **Qualquer uma com AWS no título** | 09 Cloud sobe para a Fase 2 | 03 Linux se funde ao 09 |

Quando colar a vaga, eu reordeno e escrevo aqui o que mudou e por quê.

## 7. Custos

Tudo local, open source ou free tier. Nada pago sem sua aprovação explícita antes.

| Item | Custo | Observação |
|---|---|---|
| Python, Git, VS Code, PostgreSQL local, Docker | R$ 0 | |
| Supabase, Vercel, GitHub Actions | R$ 0 | Free tier, você já usa |
| AWS | R$ 0 previsto | Free tier 12 meses. **Billing alarm é a primeira aula do módulo 09** |
| API de LLM | Sob consulta | Módulos 10 a 16. Uso mock e modelo local sempre que der. Aviso antes de qualquer custo |
| n8n, Flowise, LangChain | R$ 0 | Self-hosted via Docker |

## 8. Recalibração de 14/09/2026, depois da prova diagnóstica

**Resultado da prova: 0.** Nenhuma das 34 questões respondida.

### O que não muda

A ordem das sete fases continua igual. Ela já tinha sido montada para o cenário ruim: a Fase 1
começa por Python e fundamento, não por IA. A prova confirmou a hipótese que fundamentava essa
ordem, então não há o que reordenar. Um resultado alto teria mudado o plano. Um resultado baixo
apenas o confirma.

### O que muda, e é importante

**1. Os seus projetos deixam de ser revisão e viram material novo.** O plano original tratava
os módulos 10 a 13 como "destravar coisa que já roda nos seus projetos", o que pressupunha
familiaridade. A prova mostrou que a familiaridade não existe fora do ambiente onde a IA está
do lado. O código dos projetos continua sendo o estudo de caso, mas será lido linha a linha,
do começo, como se fosse código de estranho. O que você tem não é vantagem de conhecimento.
É vantagem de contexto: você sabe para que aquilo servia.

**2. A Fase 3 deixa de ser "a de melhor custo-benefício".** Aquela avaliação valia se as notas
provisórias 3 estivessem certas. Estavam erradas. A Fase 3 agora custa tempo normal de matéria
nova, e o marco de "conversa de entrevista pronta" ao fim da Fase 4 (fevereiro de 2027) passa
a ser otimista. Não vou mexer na data ainda: a velocidade real das quatro primeiras semanas
de Python é que diz se ela cai.

**3. A regra de avanço vale de verdade, sem exceção de cortesia.** Os seis itens da seção 5
não serão relaxados por nenhum módulo, inclusive os que "você já usa". O resultado 0 é a prova
empírica de que usar não é saber.

**4. Nada de pular o Módulo 01.** Havia a tentação de tratar Python como revisão rápida por
causa das 7.949 linhas da Central de Compras. Está descartada. Três semanas cheias.

### O que o resultado não autoriza a concluir

Que "não sabe nada". A prova mede demonstração sem consulta, que é o critério da entrevista
e do teste técnico. Ela não mede reconhecimento, leitura nem operação com ferramenta ao lado.
Um resultado 0 é compatível com "reconhece tudo e demonstra nada", e esse é o cenário mais
provável aqui, dado o volume de código em produção nos cinco projetos. A diferença entre os
dois cenários muda tudo no prazo: reconhecimento existente encurta muito o caminho até a
nota 4. Construir do zero, não.
