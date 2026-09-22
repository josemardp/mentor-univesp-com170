# Diagnóstico inicial

> Data: 13/09/2026
> Base: leitura direta (somente leitura) dos 5 projetos em `C:\projetos`.
> Regra que governa este documento: **código no repositório não prova competência.**
> Onde não pude verificar, está escrito `[não verificado]`. Não completei lacuna com suposição.

## 1. O que este diagnóstico pode e não pode afirmar

Eu li código. Isso me permite afirmar **o que existe** nos seus projetos e **quão sofisticado é**.

Isso **não** me permite afirmar o que você sabe. Um trecho excelente pode ter sido escrito
inteiro por uma IA enquanto você aprovava. A distância entre essas duas coisas é a razão
de existir este curso, e é exatamente o que o Módulo 00 vai medir.

Por isso toda competência abaixo está classificada em duas dimensões separadas:

- **Evidência no código**: o que eu verifiquei lendo. É fato.
- **Nível seu**: fica `[a aferir]` até você fazer a prova do Módulo 00. Não é fato ainda.

## 2. Correções à descrição inicial dos projetos

A tabela que você me passou descrevia os projetos de memória. Duas linhas estavam erradas,
e a correção muda a prioridade do curso.

### Central de Compras: não é FastAPI, não tem banco de dados

Foi descrito como "FastAPI + SQLite/PostgreSQL". Verificado: **zero ocorrências** de
`fastapi`, `uvicorn`, `sqlite3` ou `psycopg` em todo o repositório.
O `requirements.txt` tem **uma linha só**: `PyYAML>=6.0`.

O que é de verdade: uma aplicação de linha de comando em Python, usando só a biblioteca
padrão mais PyYAML. Persistência em arquivos YAML, CSV e Markdown no disco.

**Consequência para o curso:** você **não tem nenhum projeto com framework web backend**.
FastAPI é lacuna real, não revisão. O módulo 08 vira construção do zero, não releitura.

### Esdra Cosméticos: não é site estático

Foi descrito como "catálogo estático, GitHub Pages". Verificado: é aplicação React + Vite +
TypeScript, com `src/`, Supabase, Radix UI e service worker de PWA (`src/sw.ts`).

O catálogo estático existe, mas é **outro repositório**: `C:\projetos\esdra\catalago-esdracosmeticos`.
Foram dois projetos diferentes tratados como um.

### Automação Univesp: muito menos IA do que parecia

Playwright confirmado, e é substancial: 16 módulos coletores em `automacao/fontes/`.
Mas busca por `openai`, `anthropic`, `gemini` e `claude` em todos os `.py` encontrou
**um arquivo só** (`ava_vivo.py`). O grosso do projeto é scraping determinístico, não LLM.

`[não verificado]` se esse arquivo realmente chama um modelo ou só menciona o nome.
Vale conferir junto quando chegarmos ao módulo 10.

## 3. Competências com evidência forte no código

Estas aparecem em volume e com sofisticação real. São as candidatas mais prováveis
a virar sua narrativa de entrevista, **se você conseguir defendê-las**.

### Python (Central de Compras, mentor-univesp)

`central-compras/scripts/central_compras.py` tem **7.949 linhas e 246 funções** num arquivo só.
E não é código ingênuo. Verifiquei ali:

- Type hints modernos (`dict[str, Any] | None`, `from __future__ import annotations`)
- `@dataclass`
- Context manager próprio (`project_lock`, com `@contextlib.contextmanager`)
- Decorador próprio com `functools.wraps` (`read_session`)
- `contextvars` para cache por operação sem vazar entre threads
- Exceções customizadas (`JournalPrecisaReconciliacao`)
- Escrita atômica com `os.replace` + `os.fsync`, com retry específico para o comportamento
  do Windows quando outro processo tem o arquivo aberto
- Tratamento explícito de `NaN` e infinito antes de entrar em cálculo de ranking

Isso é nível sênior de cuidado. **Duas leituras possíveis**, e só a prova diz qual vale:
ou você entende profundamente esses padrões, ou uma IA os aplicou e você aprovou o resultado.

**Alerta de dívida técnica, independente de quem escreveu:** 7.949 linhas num arquivo único é
problema de arquitetura, e um entrevistador vai perguntar sobre isso. Trabalhamos essa resposta
no módulo 08.

### PostgreSQL e migrations (SecretárioTask, FinanceiroJE)

- SecretárioTask: 40+ migrations numeradas e sequenciais
- FinanceiroJE: 54 migrations, das quais **24 contêm `ROW LEVEL SECURITY` ou `CREATE POLICY`**

Migrations versionadas e RLS aplicado em quase metade delas é prática madura.

### pgvector e busca semântica (SecretárioTask)

Em `supabase/migrations/0002_pgvector_intelligence.sql`, verificado:
`CREATE EXTENSION vector`, coluna `vector(1536)` e uma função `match_tasks` que usa
o operador `<=>` (distância cosseno), com `match_threshold`, `match_count` e filtro por `user_id`.

Esse arquivo sozinho cobre metade do módulo 12 e boa parte do 13. É o seu melhor ativo técnico
para vaga de IA, **se você souber explicar por que 1536, por que `<=>` e não `<->`, e por que
o filtro de `user_id` precisa estar dentro da função.**

### Segurança aplicada (FinanceiroJE)

O mais denso dos cinco. Verificado:

- 15 Edge Functions em Deno/TypeScript
- `aiAdvisor/promptSanitizer.ts`: defesa explícita contra prompt injection
- `_shared/rateLimiter.ts` e `_shared/telemetry.ts`: infra compartilhada
- `user-data-export` e `user-data-purge`: portabilidade e exclusão de dados (LGPD)
- Em `smart-capture-ocr/index.ts`: valida `Bearer` token, revalida a sessão com
  `supabase.auth.getUser(token)`, e devolve código de erro nomeado por falha
  (`OCR_AUTH_REQUIRED`, `OCR_INVALID_SESSION`, `OCR_BACKEND_KEY_MISSING`)

Isso é material de aula pronto para os módulos 25 e 15.

### Testes

- central-compras: 30 arquivos de teste. O `STATUS.md` do projeto registra
  "suite completa 577 testes, 0 falhas". `[não verificado]` por mim: não rodei a suíte.
- financeiroje: Vitest + Playwright (`e2e/smoke.spec.ts`)
- mentor-univesp: `testes/test_golden.py` (golden tests)

## 4. Competências com evidência parcial

| Competência | O que existe | O que falta para virar defensável |
|---|---|---|
| React | 3 apps React reais (19 no SecretárioTask, 18 no FinanceiroJE, 177 arquivos TS/TSX) | `[a aferir]` se você escreve um componente com hooks do zero sem consultar |
| TypeScript | Usado em tudo, `tsconfig` estrito no SecretárioTask | Tipos avançados (generics, utility types) não verifiquei em uso |
| Git | 5 repos ativos, commits frequentes | Branch, merge, conflito e rebase: nenhuma evidência de uso. Seu fluxo é commit direto na main |
| Playwright | 16 coletores + e2e no FinanceiroJE | Sólido em scraping. Falta Playwright como ferramenta de **teste** |
| Function calling | `[não verificado]` | Não encontrei definição de tool schema em lugar nenhum |

## 5. Lacunas reais, sem evidência nenhuma

Nenhum arquivo em nenhum dos cinco projetos toca nestes assuntos:

| Lacuna | Gravidade para vaga de IA |
|---|---|
| **FastAPI / backend Python com framework** | Alta. É o que mais aparece em vaga de IA no Brasil |
| **RAG completo** | Alta. Você tem embeddings e pgvector, mas não o pipeline (chunking, retrieval, reranking, geração com citação) |
| **Agentes com tools** | Alta. Nenhum loop de agente, nenhum tool schema |
| **LangChain / LangGraph / CrewAI** | Alta. Zero ocorrências |
| **MCP (servidor próprio)** | Média. Você **usa** MCP todo dia, mas nunca escreveu um |
| **n8n / Flowise / OpenClaw** | Média |
| **Cloud (AWS/Azure/GCP)** | Média. Só Supabase e Vercel, que são PaaS |
| **Docker** | Média |
| **Linux** | Média. Ambiente é Windows, e o `atomic_write_text` mostra que você lida com peculiaridades do Windows, não do POSIX |
| **Java** | Baixa para vaga de IA. Deixar por último |
| **Multiagentes** | Média |

## 6. A lacuna que não é técnica

Todos os cinco projetos foram construídos com forte assistência de IA. O código é bom.
A pergunta da entrevista não vai ser "esse código é bom". Vai ser:

> "Me explica por que você escolheu escrever direto no arquivo em vez de usar um banco."

Se a resposta vier pronta na sua cabeça, a competência é sua. Se você precisar abrir o
código para lembrar, ela ainda não é. **Esse é o único diagnóstico que importa, e ele
depende da prova do Módulo 00, não de mim.**

## 7. Dados sensíveis encontrados

Encontrei quatro arquivos sensíveis nos projetos-fonte. **Não li o conteúdo de nenhum,
e nada disso será copiado para dentro do curso:**

- `secretario-task/.env`
- `esdra/esdracosmeticos/.env`
- `financeiroje/.env.local`
- `mentor-univesp/automacao/storage_state.json` (cookie de sessão do AVA)

Rodei `git check-ignore` nos quatro. **Todos estão corretamente ignorados.** Nenhuma ação necessária.

## 8. Ordem recomendada, e por quê

A ordem padrão do currículo (00 a 29) está certa em espírito mas erra em duas coisas
para o seu caso específico. O `PLANO_GERAL.md` traz a ordem ajustada e a justificativa.

Resumo: seu gargalo não é IA, é **fundamento de backend e de Git colaborativo**. Você já opera
na camada mais alta (pgvector, RLS, multimodalidade) sem ter a camada de baixo firme. Isso
aguenta enquanto a IA está do seu lado, e cede na hora do teste técnico.
