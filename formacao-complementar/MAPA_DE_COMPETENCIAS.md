# Mapa de competências

> Atualizado em: 14/09/2026, depois da prova diagnóstica do Módulo 00.
> Resultado da prova: **0**. Nenhuma questão respondida. Registro em
> `privado/formacao-complementar/00-fundamentos/RESPOSTAS_JOSEMAR.md` (acervo privado).

## A escala

| Nota | Significa |
|---|---|
| 0 | Desconheço. Não sei nem o que é |
| 1 | Reconheço o nome, sei mais ou menos para que serve |
| 2 | Explico o conceito para outra pessoa, sem código na frente |
| 3 | Implemento **com ajuda** (documentação, exemplo, IA) |
| 4 | Implemento **sozinho**, sem IA, e depuro quando quebra |
| 5 | Ensino, escolho entre alternativas e defendo o trade-off |

**A nota 4 é a linha da contratação.** Abaixo dela você depende de ferramenta na hora do teste.
Nota 3 com IA desligada vira nota 1 na prática.

## Como as colunas funcionam

- **Evidência**: o que eu verifiquei lendo seu código. É fato sobre o repositório.
- **Provisório**: minha estimativa a partir da evidência. **Não é sua nota.** É hipótese.
- **Aferido**: sua nota real, medida pela prova. `0` = não demonstrado na prova de 14/09/2026.
  `n/c` = a prova não cobria esse assunto, então continua sem medição.
- **Meta**: onde precisa chegar para a vaga-alvo.

Nunca use a coluna Provisório em currículo, LinkedIn ou entrevista. Ela não foi medida.

**O que o `0` aferido significa, e o que não significa.** Significa: você não conseguiu
demonstrar o assunto no papel, sem consulta e sem IA. É o critério da vaga, e é o único
que vale aqui. **Não** significa que você desconhece o assunto no sentido comum da palavra:
você opera Supabase todo dia, tem 94 migrations escritas e pgvector rodando em produção.
Reconhecer e usar com IA do lado é uma coisa. Demonstrar sozinho é outra. A prova mede a
segunda, e a distância entre as duas é exatamente o conteúdo deste curso.

## Tabela

| # | Competência | Evidência no seu código | Provisório | Aferido | Meta |
|---|---|---|---|---|---|
| 1 | Python | 7.949 linhas, 246 funções, decorador e context manager próprios (central-compras); 50 arquivos (mentor-univesp) | 3 | 0 | 5 |
| 2 | JavaScript | Presente via TS nos 3 apps React | 2 | 0 | 4 |
| 3 | TypeScript | 177 arquivos TS/TSX (financeiroje), 54 (secretario-task) | 3 | 0 | 4 |
| 4 | Java | Nenhuma | 0 | n/c | 1 |
| 5 | Linux | Nenhuma. Ambiente é Windows | 1 | n/c | 3 |
| 6 | Git | 5 repos ativos, commits frequentes. **Sem evidência de branch, merge ou conflito** | 2 | n/c | 4 |
| 7 | GitHub | GitHub Pages, Actions (workflow `guia-diario.yml`), Secrets | 2 | n/c | 4 |
| 8 | HTTP | Headers CORS, Bearer, códigos de status nas Edge Functions | 2 | 0 | 4 |
| 9 | REST | APIs consumidas e Edge Functions expostas | 2 | 0 | 4 |
| 10 | SQL | 94 migrations somando os dois projetos Supabase | 3 | 0 | 4 |
| 11 | PostgreSQL | Functions plpgsql, triggers, constraints, lock otimista (`0013_task_version_optimistic_lock`) | 3 | 0 | 4 |
| 12 | Supabase | Auth, RLS, Storage, 15 Edge Functions, migrations | 3 | 0 | 5 |
| 13 | React | 3 apps, React 18 e 19, hooks, Zustand, React Query | 3 | n/c | 4 |
| 14 | FastAPI | **Nenhuma.** Confirmado: não existe em nenhum projeto | 0 | n/c | 4 |
| 15 | Cloud (AWS) | Nenhuma. Só PaaS (Supabase, Vercel) | 0 | n/c | 3 |
| 16 | IA generativa | OCR multimodal, aiAdvisor, systemPrompt estruturado | 3 | 0 | 5 |
| 17 | Prompt engineering | `promptSanitizer.ts`, `systemPrompt.ts`, `coachAIGuardrails.ts` | 3 | n/c | 5 |
| 18 | Embeddings | `vector(1536)` + `match_tasks` com `<=>` | 2 | 0 | 5 |
| 19 | Vector database | pgvector em produção. **Sem índice HNSW/IVFFlat verificado** | 2 | 0 | 4 |
| 20 | RAG | **Nenhuma.** Tem as peças (embeddings + busca), não tem o pipeline | 1 | 0 | 5 |
| 21 | Function calling | **Nenhuma.** Nenhum tool schema encontrado | 0 | 0 | 5 |
| 22 | Agentes de IA | **Nenhuma.** Nenhum loop de agente | 1 | 0 | 5 |
| 23 | Multiagentes | Nenhuma | 0 | n/c | 3 |
| 24 | LangChain | Nenhuma | 0 | n/c | 3 |
| 25 | LangGraph | Nenhuma | 0 | n/c | 4 |
| 26 | CrewAI | Nenhuma | 0 | n/c | 2 |
| 27 | MCP | **Usa** MCP diariamente. **Nunca escreveu um servidor** | 1 | n/c | 4 |
| 28 | n8n | Nenhuma | 0 | n/c | 3 |
| 29 | Flowise | Nenhuma | 0 | n/c | 2 |
| 30 | OpenClaw | Nenhuma | 0 | n/c | 2 |
| 31 | Segurança | RLS em 24 migrations, sanitização de prompt, rate limit, LGPD (export/purge) | 3 | 0 | 5 |
| 32 | Testes | 577 testes (central-compras, não rodei), Vitest, Playwright, golden tests | 3 | n/c | 4 |
| 33 | Deploy | GitHub Pages, Vercel, Supabase, GitHub Actions | 2 | n/c | 3 |
| 34 | Observabilidade | `telemetry.ts` compartilhado nas Edge Functions | 2 | n/c | 3 |

## Leitura rápida da tabela

**Soma provisória: 58 de 170 possíveis (34%). Soma aferida: 0 nas 16 competências que a
prova cobriu.** As outras 18 continuam sem medição e só serão medidas nas provas cumulativas.

O provisório errou, e errou para baixo em direção nenhuma: errou de eixo. A estimativa de
3 em Python, SQL, PostgreSQL, Supabase e IA generativa vinha da qualidade do código lido.
A prova mostrou que a qualidade do código não migra para a cabeça de quem aprovou o código.
Essa é a lição de método mais cara deste curso, e ela vale para tudo que vier: **só entra na
coluna Aferido o que passou por prova com IA desligada.**

O padrão que já saltava aos olhos no provisório continua de pé e agora tem confirmação:
você tem código sofisticado em coisas caras e difíceis (pgvector, RLS, multimodalidade) e
nada firme nos degraus de baixo (FastAPI, function calling, cloud).

Isso é a assinatura de quem construiu com IA. A IA não ensina em ordem de dificuldade,
ela entrega o que foi pedido. Você pediu coisas ambiciosas e recebeu coisas ambiciosas,
pulando os degraus do meio.

**As 5 lacunas que mais custam caro numa vaga de IA hoje:**

1. Function calling (0, meta 5). É o assunto mais perguntado em entrevista de IA em 2026
2. RAG (1, meta 5). Você tem as peças soltas e nunca montou
3. Agentes (1, meta 5). Idem
4. FastAPI (0, meta 4). Aparece em quase toda vaga
5. Embeddings (2, meta 5). Está em produção no seu app e você não sabe defender

**A boa notícia:** as lacunas 2, 3 e 5 são as mais rápidas de fechar, porque a infraestrutura
já existe nos seus projetos. Você não precisa começar do zero, precisa entender o que já rodou.

## Registro de reavaliação

| Data | Evento | O que mudou |
|---|---|---|
| 13/09/2026 | Linha de base a partir da leitura de código | Tabela criada. Coluna Aferido vazia |
| 14/09/2026 | Prova diagnóstica do Módulo 00, resultado 0 | Coluna Aferido preenchida: `0` nas 16 competências cobertas, `n/c` nas 18 não cobertas. Nenhuma competência está em 4. Ordem do `PLANO_GERAL.md` mantida |
