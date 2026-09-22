# Formação Complementar

> Trilha técnica em IA e automação, estudada em paralelo ao bacharelado na Univesp.
> Morava no repositório `formacao-ia-automacao` até 22/09/2026; agora vive aqui.
> A prova diagnóstica e as respostas ficam no acervo privado (`privado/formacao-complementar/00-fundamentos/`,
> que aponta para o Google Drive), fora do repositório público.

> Currículo técnico pessoal do Josemar. Objetivo: concorrer a vaga de IA sem depender de IA.
> Criado em 13/09/2026.

## Onde estou agora

| | |
|---|---|
| **Módulo atual** | `00-fundamentos` (prova diagnóstica) |
| **Próximo** | `01-python` |
| **Progresso** | 0 de 30 módulos |
| **Horas estudadas** | 0 |
| **Nota do mapa** | 58/170 provisório, **0 aferido** |
| **Projetos integradores** | 0 de 12 |
| **Velocidade** | Padrão (8 a 10h/semana) |
| **Previsão de término** | ~junho de 2027 |
| **Vaga-alvo** | Não definida |

## O que fazer HOJE

**Fazer a prova diagnóstica.** Duas formas, escolha uma:

- **No celular ou em qualquer aparelho** (recomendado): https://claude.ai/code/artifact/5d0db85f-a31c-466f-b6e1-3de0dc347377
  Salva sozinho e sincroniza entre os aparelhos. Dá para começar no celular e terminar no PC.
  O código-fonte dessa página é `privado/formacao-complementar/00-fundamentos/prova-web.html`.
- **No editor:** `privado/formacao-complementar/00-fundamentos/MODULO_00_DIAGNOSTICO.md`, respondendo em
  `RESPOSTAS_JOSEMAR.md`, na mesma pasta.

90 a 120 minutos, de uma vez só, sem IA, sem consultar seus projetos, sem Google.

Nada mais. Não comece o módulo 01, não leia o gabarito (não existe ainda), não adiante nada.
Todo o resto do plano depende dessa medição, e uma medição contaminada estraga 9 meses.

## O que NÃO estudar ainda

| Não agora | Por quê | Quando |
|---|---|---|
| LangChain, LangGraph, CrewAI | Framework antes do mecanismo vira decoreba | Fase 5, ~semana 22 |
| n8n, Flowise, OpenClaw | Idem, e escondem ainda mais | Fase 5 |
| RAG | Precisa de embeddings e API firmes antes | Fase 4, ~semana 19 |
| Agentes | Precisa de function calling antes | Fase 4, ~semana 22 |
| AWS | Precisa de Linux e Docker antes | Fase 6 |
| Java | Retorno quase zero para vaga de IA | Último, se sobrar |
| Multiagentes | Precisa de agente único funcionando | Fase 5 |

A tentação vai ser pular direto para agentes e LangChain, porque é o que está no nome da vaga.
**Não pule.** O diagnóstico mostrou que seu problema não é falta de IA, é falta de chão.

## Documentos vivos

| Arquivo | Para quê | Quando mexer |
|---|---|---|
| [PLANO_GERAL.md](PLANO_GERAL.md) | Ordem dos módulos, decisões, cronograma | A cada 4 módulos |
| [DIAGNOSTICO_INICIAL.md](DIAGNOSTICO_INICIAL.md) | O que o código prova e o que não prova | Só se mudar projeto |
| [MAPA_DE_COMPETENCIAS.md](MAPA_DE_COMPETENCIAS.md) | 34 competências, escala 0 a 5 | Ao fim de cada módulo |
| [PROGRESSO.md](PROGRESSO.md) | Horas, módulos, notas | Toda sessão |
| [DIARIO_DE_ESTUDOS.md](DIARIO_DE_ESTUDOS.md) | O que aprendi, o que não entendi | Toda sessão |
| [REVISOES.md](REVISOES.md) | Revisão espaçada D+1, D+7, D+30 | Toda sessão |
| [FORMULARIO_CAPACITACAO_REVISAO.md](FORMULARIO_CAPACITACAO_REVISAO.md) | Uma ficha por tecnologia | Ao fim de cada módulo |

## Módulos

**Fase 1, firmar o chão**
[00 Fundamentos](00-fundamentos/) · [01 Python](01-python/) · [04 Git e GitHub](04-git-github/) · [03 Linux](03-linux-terminal/)

**Fase 2, backend**
[05 HTTP e REST](05-http-rest-apis/) · [06 Bancos de dados](06-bancos-dados/) · [08 Backend FastAPI](08-backend/)

**Fase 3, destravar o que já uso**
[10 IA generativa](10-ia-generativa/) · [11 Prompt engineering](11-prompt-engineering/) · [12 Embeddings](12-embeddings/) · [13 Vector database](13-vector-database/)

**Fase 4, o que a vaga pede**
[14 RAG](14-rag/) · [15 Function calling](15-function-calling/) · [16 Agentes](16-agentes-ia/)

**Fase 5, frameworks**
[19 LangChain](19-langchain/) · [20 LangGraph](20-langgraph/) · [17 Multiagentes](17-multiagentes/) · [18 MCP](18-mcp/) · [21 CrewAI](21-crewai/) · [22 n8n](22-n8n/) · [23 Flowise](23-flowise/) · [24 OpenClaw](24-openclaw/)

**Fase 6, profissionalizar**
[25 Segurança](25-seguranca/) · [26 Testes e observabilidade](26-testes-observabilidade/) · [09 Cloud](09-cloud-deploy/) · [07 React](07-react-web/) · [02 JS e TS](02-javascript-typescript/)

**Fase 7, fechar**
[27 Projetos integradores](27-projetos-integradores/) · [28 Entrevistas](28-entrevistas/) · [29 Revisão final](29-revisao-final/)

## Como este curso é construído

Os módulos são gerados **um de cada vez**, conforme você avança. Só o 00 e o 01 existem
por inteiro. As outras 28 pastas têm um `README.md` de stub dizendo o que vai ter ali.

Isso é de propósito: módulo gerado com 6 meses de antecedência ignora o que a prova
revelou e o que você aprendeu no caminho.

## Regras que valem para o curso inteiro

1. **Os 5 projetos-fonte são somente leitura.** Nunca editar, mover ou commitar neles
2. **Nenhum dado pessoal, financeiro, institucional ou de terceiro entra aqui**
3. **Domínio é nota 4:** implementar sozinho, sem IA, e depurar quando quebra
4. Exercícios marcados **sem IA** são sem IA. Colar resposta de IA ali não engana ninguém
   além de você mesmo, daqui a 9 meses, numa sala de entrevista
5. **Pode estudar com qualquer IA (Claude, Antigravity, Codex, ChatGPT), não só esta.**
   O curso está todo em arquivos de texto nesta pasta; qualquer IA que abrir a pasta lê
   o mesmo material. Duas regras para trocar de IA sem perder o rumo:
   - **Para entender conceito, qualquer IA vale.** É aula, não é prova.
   - **Para exercício ou prova marcados "sem IA", a proibição vale para qualquer IA**,
     não só para esta. Usar outra IA ali é a mesma armadilha que gerou o resultado 0
     na prova diagnóstica, só que disfarçada.
   - **O estado do curso mora nos arquivos, nunca só numa conversa.** Depois de estudar
     com outra IA, peça para ela atualizar `PROGRESSO.md` e `DIARIO_DE_ESTUDOS.md`. Assim
     qualquer IA que você abrir depois (inclusive esta) sabe onde você parou.
