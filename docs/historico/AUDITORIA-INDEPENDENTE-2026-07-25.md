# Auditoria independente — robô do guia de estudos Univesp

**Data da auditoria:** 25/07/2026  
**Escopo:** código local, execução no GitHub Actions, site publicado e AVA autenticado  
**Repositório auditado:** `esdraaline/mentor-univesp-com170`

## 1. Resumo executivo

O robô já resolve bem a descoberta das quatro disciplinas, a leitura básica do Moodle, o cronograma regular e a exposição da origem dos prazos.  
O risco mais grave é de **falha aberta**: uma coleta vazia ou um DOM alterado pode ser gravado como `status: ok`, levando site e e-mail a dizerem “tudo em dia”.  
O modelo de ação também perde obrigações com mais de uma fase: a COM170 tem submissão até 01/08 e avaliação por pares até 04/08, mas a fila mostra somente a primeira.  
A propagação entre módulos muda uma prioridade em um prazo aparente, mesmo sem o código comprovar a dependência; isso viola a regra “prazo nunca é estimado”.  
O `data.json` público contém nomes e textos de colegas; um post real com telefone satisfaz o filtro e poderia ser publicado sem redação.  
Fóruns de discussão única têm centenas ou mais de mil posts, mas o cache retém dez e a disciplina publica quinze, silenciosamente.  
Não há testes, retry/backoff, contrato de saúde por fonte nem alerta externo de ausência de execução.  
Recomendação: não confiar na ferramenta como única agenda até concluir os itens P0 deste relatório.

## 2. Cobertura e método

### 2.1 O que foi verificado ao vivo

A auditoria entrou no AVA com a sessão autenticada pelo próprio Josemar, sem pedir, ler ou gravar senha. Nenhum formulário foi enviado e nenhum estado acadêmico foi alterado.

Foram inspecionados:

- as quatro disciplinas ativas: COM100, SOC100, LET110 e COM170;
- todas as seções e os 99 itens visíveis na página dos cursos;
- todas as 43 páginas de conteúdo vigente acessíveis, incluindo quizzes, SCORM, lives, videoaulas, textos-base, formulários, referências e páginas de síntese;
- os 19 fóruns visíveis, incluindo os 12 fóruns de discussão única e os tópicos separados de Avisos e dos grupos;
- calendário, notificações, mensagens, boletim das quatro disciplinas, cronograma oficial e os dois planos de ensino vinculados;
- o site publicado e os dez últimos runs do GitHub Actions.

O AVA mostrava três notificações não lidas, três eventos futuros de fechamento de quiz e nenhuma conversa não lida. O boletim da COM170 exibia **“Erro no cálculo do item de nota Média AVA”**.

### 2.2 Verificações locais

- Os nove arquivos Python têm sintaxe válida.
- Não existe teste versionado.
- Foram reproduzidos, com entradas mínimas, os casos de horário inventado, ordinal não reconhecido, virada de ano errada, prazo aplicado à seção inteira, propagação sem dependência comprovada e coleta vazia aceita como sucesso.
- O worktree permaneceu limpo antes da criação deste relatório.

## 3. Inventário AVA × robô

| Tipo de dado ou obrigação no AVA | Cobertura atual | Impacto da lacuna | Onde o dado mora | Como capturar com segurança |
|---|---|---:|---|---|
| Disciplinas ativas | **Sim, com ressalva** | Ruído e consumo de orçamento se cursos antigos voltarem a aparecer | “Meus cursos” | Manter descoberta automática, mas filtrar estado ativo e comparar a contagem com o último run |
| Seções, itens, tipo e link | **Sim** para o DOM principal | Pode omitir item atrás de subseção/página separada | Página do curso e `/course/section.php?id=...` | Ler também os links de seção e reconciliar por `cmid`, sem duplicar subseções |
| Status de conclusão | **Parcial** | Pode cobrar item concluído ou esconder pendência | `.activity-completion` e API de conclusão | Normalizar estados estruturados; não comparar somente textos exatos em português |
| Bloqueios e dependências | **Parcial** | Prioridade errada ou prazo falso | `.availabilityinfo` | Extrair a atividade predecessora citada e montar grafo explícito por nome/`cmid` |
| Data de abertura/fechamento do item | **Parcial** | Perde prazo quando calendário falha | Página individual do quiz/tarefa/workshop | Extrair os campos “Aberto”, “Fecha”, fases e status durante a conferência do item |
| Cronograma semanal regular | **Sim** | Baixo no bimestre atual | Link oficial do curso | Manter; validar cabeçalhos, número de semanas e ano |
| Arquivo `cronograma.ics` | **Não** | Conveniência e redundância de datas | Botão gerado na página do cronograma | Consumir o ICS como quarta fonte e reconciliar divergências |
| Calendário de ações | **Parcial** | Pode perder eventos depois do 50º | API `core_calendar_get_action_events_by_timesort` | Particionar a janela temporal e deduplicar, registrando se algum lote atingiu 50 |
| Eventos de curso, usuário e lives | **Parcial/Não** | Pode perder live, prova ou evento sem ação Moodle | Calendário DOM/API de eventos | Fazer união API + DOM sempre, não apenas fallback quando a API volta vazia |
| Quiz | **Parcial** | Não acompanha tentativa, envio, nota ou erro | Página do quiz, calendário e boletim | Ler datas, tentativas, estado de envio e nota; nunca iniciar tentativa |
| Tarefa/arquivo | **Parcial** | Não distingue “grupo entregou” de “eu preciso entregar” | Página de tarefa e notificações | Ler status de submissão, responsável, feedback e prazo |
| Workshop/revisão por pares | **Parcial e insuficiente** | **Pode perder nota** na fase de avaliação | Página do workshop e aviso | Criar ações separadas por fase: submissão, alocação, avaliação e fechamento |
| Formulário externo | **Parcial** | Pode ficar sem confirmação de resposta | Página Moodle + Microsoft Forms | Registrar que é externo e exigir confirmação do Moodle; não enviar automaticamente |
| Live com facilitador | **Parcial** | Pode perder presença/nota e gravação | LTI, aviso e fórum | Unir evento, aviso, link de sala/gravação e estado de participação |
| Fórum “Avisos” | **Parcial** | Pode perder critério, prazo ou correção | Tópicos separados no fórum | Prioridade absoluta para posts de docentes/facilitadores; não truncar silenciosamente |
| Fórum geral/temático | **Parcial e ruidoso** | Aviso útil se perde entre posts; risco de privacidade | Discussão única com centenas de posts | Ler incrementalmente por ID de post e papel do autor; não publicar texto de aluno |
| Fórum do grupo | **Parcial** | Pode perder entrega, representante ou revisão por pares | Fórum restrito do grupo | Manter leitura privada; gerar apenas evento estruturado e link, sem corpo público |
| Notificações | **Parcial** | Feedback e abertura não viram ação | Popup/API de notificações | Classificar assunto e vincular por `cmid`; manter até resolvido, não só enquanto “não lida” |
| Mensagens privadas | **Metadado apenas** | Prazo enviado por mensagem não é compreendido | Mensagens Moodle | Processar conteúdo somente em armazenamento privado e publicar apenas alerta genérico |
| Boletim/notas | **Não** | Não detecta nota ausente ou erro de cálculo | Relatório de notas | Leitor somente leitura; alertar ausência, mudança e erro sem publicar nota pessoal |
| Plano de ensino | **Link apenas** | Critério pode divergir do aviso | Página oficial da disciplina | Extrair critérios como regra de referência e sinalizar divergências |
| Calendário geral de provas | **Não** | **Pode perder prova presencial** | Manual/Calendário de Provas | Adicionar fonte oficial e ações de prova por disciplina/polo |
| Biblioteca e referências | **Link/conteúdo do curso apenas** | Conveniência | Painel, Pearson, Minha Biblioteca | Não precisa varrer acervo; basta manter atalhos e leituras explicitamente exigidas |
| Saúde/frescura da coleta | **Não** | “Tudo em dia” falso | Todas as fontes | Publicar cobertura por fonte, contagens, erros e último sucesso válido |

## 4. Achados por severidade

### CRÍTICO 1 — coleta vazia é publicada como sucesso e “tudo em dia”

**Fato observado:** `automacao/coletar.py:753-756` aceita qualquer resultado de “Meus cursos”; `automacao/coletar.py:1041-1062` grava `status: ok` sem validar quantidade de cursos, seções, eventos ou fontes.

**Cenário reproduzido:** o coletor devolveu `courses=[]`, `notificacoes=[]`, `mensagens=[]` e `eventos=[]`. Resultado:

```text
returncode=0, status=ok, courses=0, acoes=0
```

O render então cai em `automacao/render.py:183-185` e publica “Nada pendente. Tudo em dia”.

**Impacto:** omissão total de todas as obrigações, com aparência de sucesso.

**Correção sugerida:** introduzir contrato de saúde e falhar fechado. Uma queda abrupta de quatro para zero cursos, curso sem seções, cronograma vazio ou calendário incompleto deve preservar o último retrato válido e exibir “coleta incompleta”.

```diff
- saida = {"status": "ok", ...}
+ validar_cobertura(dados, anterior)
+ saida = {
+   "status": "ok",
+   "source_health": dados["source_health"],
+   "last_success_at": agora,
+   ...
+ }
```

O validador não deve fixar “quatro cursos para sempre”; deve comparar com o run anterior e exigir invariantes mínimas.

### CRÍTICO 2 — conteúdo pessoal de colegas é publicado em repositório e site públicos

**Fato observado:** `automacao/coletar.py:522-529` considera “interessante” qualquer post com palavras genéricas como “atividade” e “grupo”; `automacao/coletar.py:537-543` mantém autor e 400 caracteres; `automacao/render.py:236-242` publica até 300 caracteres. `docs/data.json:63-131` já contém nomes completos e relatos pessoais de alunos.

**Cenário reproduzido:** um post real do fórum do grupo contém um telefone no primeiro parágrafo e também a palavra “trabalho”. A mesma entrada anonimizada passou por `post_interessa()` e `_preparar()` com o telefone preservado. Os telefones específicos vistos nesta auditoria não foram encontrados no histórico Git, mas o caminho de vazamento está confirmado.

**Impacto:** exposição de dados pessoais, falas e possivelmente telefone/e-mail em site público e histórico Git.

**Correção sugerida:**

1. parar imediatamente de publicar corpo e nome de aluno;
2. publicar somente `{curso, tipo_de_alerta, data, link}` ou conteúdo de autores institucionais previamente identificados;
3. aplicar redação de telefone, e-mail, CPF e links pessoais antes de qualquer persistência;
4. separar o coletor em repositório privado e publicar apenas um artefato sanitizado no Pages público;
5. auditar o histórico Git por PII antes de decidir se precisa reescrevê-lo.

### CRÍTICO 3 — revisão por pares tem duas fases, mas a fila guarda apenas um prazo

**Fato observado ao vivo:** o aviso da COM170 informa:

- submissão: 27/07 a 01/08 23:59;
- avaliação por pares: 02/08 a 04/08 23:59.

O site publicado mostra apenas “Módulo 6 vence 01/08”. `automacao/coletar.py:874-887` retorna o primeiro prazo que casa com a seção, e `automacao/coletar.py:934-948` guarda um único `prazo`.

**Cenário concreto:** após a entrega em 01/08, não existe uma ação independente lembrando que a avaliação do trabalho de outro grupo vale nota e fecha em 04/08.

O mesmo casamento é feito pelo título da seção. Em teste, um aviso “Módulo 4: entrega do portfólio” atribuiu 01/08 tanto ao item “Portfólio” quanto a uma “Leitura opcional” da mesma seção.

**Impacto:** perda de atividade que vale nota e possibilidade de prazo falso em item não relacionado.

**Correção sugerida:** o objeto principal deve ser **obrigação/fase**, não seção:

```json
{
  "course": "COM170",
  "entity": "revisao_pares_q1",
  "phase": "avaliacao",
  "opens_at": "2026-08-02T00:00:00-03:00",
  "due_at": "2026-08-04T23:59:00-03:00",
  "source_url": "...",
  "confidence": "explicit"
}
```

Se o aviso não identifica um `cmid`, o site deve mostrar “prazo do Módulo 6/7” no nível do módulo, sem copiá-lo para cada item.

### CRÍTICO 4 — propagação de urgência transforma uma hipótese de dependência em prazo

**Fato observado:** `automacao/coletar.py:959-1002` procura somente a família e o número da seção. Uma ação anterior sem prazo herda o prazo de qualquer seção numericamente posterior. A função não lê a condição real de disponibilidade.

**Cenário reproduzido:** uma “Leitura sem dependência declarada” no Módulo 1 herdou 01/08 do Módulo 4 e recebeu `destrava: true`.

No caso real atual, o resultado para o quiz do Módulo 1 está correto porque o aviso e o AVA confirmam a cadeia M1 → M2 → M3 → M4. O problema é que o código chegou ao resultado por coincidência de numeração, não por essa evidência.

**Impacto:** a pior falha definida pelo projeto: prazo que parece oficial, mas foi inferido.

**Correção sugerida:** separar prazo de prioridade:

```diff
- a["prazo"] = prazo
- a["prazo_fonte"] = fonte
+ a["prioridade_herdada_ate"] = prazo
+ a["destrava_obrigacao_id"] = obrigacao_destino
+ # a["prazo"] continua nulo
```

Só definir `destrava` quando a disponibilidade citar explicitamente a atividade predecessora.

### ALTO 5 — parser de texto inventa horário e erra ordinal, ano e semântica

**Arquivos/linhas:** `automacao/coletar.py:261-316`.

**Cenários reproduzidos:**

| Entrada | Saída atual | Problema |
|---|---|---|
| `entregue até 26/07` | `26/07/2026 23:59` | 23:59 não existe na fonte |
| `até 1º de agosto` | nenhuma data | formato comum ignorado |
| `até 10 de janeiro`, post de dez/2026 | 10/01/2026 | vira passado em vez de 2027 |
| `LIVE INICIAL: realizada em 23/07` | tipo `inicio`, 23:59 | `inicia` casa dentro de `inicial` |

O último caso está no `docs/data.json` atual: “LIVE INICIAL” foi classificada como abertura.

**Impacto:** falsa precisão, prazo escondido e classificação errada de evento.

**Correção sugerida:** guardar precisão separada (`date`, `datetime`, `time_unknown`), usar limites de palavra nos gatilhos e inferir ano pelo contexto temporal do post. Sem hora explícita, renderizar “até 26/07 — horário não informado”.

### ALTO 6 — fóruns grandes são truncados silenciosamente e o filtro privilegia ruído

**Fato observado ao vivo:** fóruns de discussão única tinham, entre outros, 928 posts (COM100), 1.324 posts (SOC100) e 868 posts (LET110). O filtro atual selecionou principalmente respostas de alunos porque “atividade”, “grupo” e “avaliação” são gatilhos genéricos.

**Arquivos/linhas:**

- `automacao/coletar.py:522-529` — filtro genérico;
- `automacao/coletar.py:534-560` — dez posts por discussão;
- `automacao/coletar.py:563-631` — orçamento global sem indicador de truncamento;
- `automacao/coletar.py:863` — quinze avisos por curso.

**Cenário concreto:** onze posts novos de alunos que contenham “atividade” empurram uma orientação mais antiga do facilitador para fora dos dez persistidos. Não há flag de cobertura incompleta.

**Impacto:** aviso válido pode desaparecer, enquanto nomes e textos irrelevantes ocupam o site.

**Correção sugerida:** duas passagens: primeiro Avisos/autores institucionais e posts do próprio grupo; depois demais fóruns. Persistir IDs de post, papel do autor e `coverage.truncated=true`. Qualquer truncamento de fonte capaz de conter prazo deve gerar alerta operacional.

### ALTO 7 — calendário pode voltar parcialmente e impedir o fallback completo

**Arquivos/linhas:** `automacao/coletar.py:396-478`.

**Fato observado:** o limite de 50 foi corrigido e a API retornou os três eventos atuais, iguais aos três fechamentos vistos no calendário ao vivo. Porém não há partição/paginação. Se a API devolver exatamente 50, o código considera a coleta completa. Além disso, qualquer lista não vazia impede a união com o DOM.

`core_calendar_get_action_events_by_timesort` cobre eventos de ação; lives e eventos de curso sem ação podem ficar fora. A leitura DOM só ocorre quando a API retorna zero.

**Cenário concreto:** 55 eventos na janela → 50 entram, cinco somem, o fallback não roda e não há aviso.

**Correção sugerida:** particionar por janelas menores, deduplicar por ID e sempre unir API + DOM. Se um lote atingir 50, subdividi-lo ou marcar cobertura incompleta.

Também aproveitar `item_aberto()` para extrair datas. As páginas dos três quizzes exibiam ao vivo “Aberto: 20/07 00:00” e “Fecha: 02/08 23:59”, mas `automacao/coletar.py:645-655` lê o corpo apenas para procurar frases de encerramento.

### ALTO 8 — falha operacional pode ocorrer sem aviso útil ao aluno

**Fato observado:**

- não há retry/backoff de navegação;
- várias exceções viram lista vazia;
- falha não tratada antes do passo de e-mail impede o próprio alerta;
- `automacao/enviar_email.py:152-160` engole falha SMTP;
- não existe heartbeat externo para detectar que o cron não rodou;
- todos os dez runs recentes consultados eram `workflow_dispatch`; o agendamento das 8h ainda não foi exercitado com este código.

**Impacto:** o robô pode deixar de atualizar justamente no dia crítico sem que Josemar receba uma mensagem.

**Correção sugerida:** retries com jitter para GET/navegação, um segundo attempt da coleta, timeout do job, e heartbeat externo que alerte se não houver sucesso até um horário definido. O e-mail de falha deve ser enviado por um caminho independente do coletor.

### ALTO 9 — notificações, feedback, mensagens e boletim não alimentam a fila

**Arquivos/linhas:** `automacao/coletar.py:481-511`, `automacao/render.py:256-269`.

**Fato observado ao vivo:**

- três notificações avisavam abertura da Atividade Avaliativa S2;
- havia notificação de feedback devolvido para uma tarefa;
- o boletim da COM170 mostrava erro no cálculo de “Média AVA”;
- não havia mensagem privada não lida no momento da auditoria.

O robô mostra assuntos não lidos, mas não os vincula a obrigação nem mantém o alerta depois que a notificação é lida. Ele não lê o boletim.

**Impacto:** feedback que exige correção, erro de nota ou aviso privado podem ficar fora de “o que faço agora”.

**Correção sugerida:** criar uma caixa privada de sinais, relacionar notificação por URL/`cmid`, manter estado “aberto/resolvido” e ler o boletim somente para detectar ausência, mudança ou erro. Nota e conteúdo de mensagem não devem ir ao JSON público.

### MÉDIO 10 — classificação “vale nota” é heurística e não representa os pesos reais

**Arquivo/linhas:** `automacao/coletar.py:661-672`.

**Fato observado:** na COM170, todo item dentro de seção “Módulo” é marcado como valendo nota, embora o aviso diga que “Módulo concluído” é uma unidade de avaliação. O aviso ainda contém uma contradição: diz “nove atividades contáveis”, mas enumera dez critérios.

Nas disciplinas regulares, o reconhecimento depende de palavras do título. Uma mudança editorial pode retirar o selo de material que vale participação.

**Impacto:** percepção errada de peso e incapacidade de prever nota com confiança.

**Correção sugerida:** regras versionadas por modelo de disciplina e período, com evidência de origem. Divergências como “nove × dez” devem aparecer como “regra inconsistente — confirme com facilitador”, nunca ser resolvidas silenciosamente.

### MÉDIO 11 — status textual, limite de 45 itens e AIA fixo são frágeis

**Arquivos/linhas:** `automacao/coletar.py:804-855`.

**Fato observado:** o código compara exatamente `Concluído` e `Pendente`. Em subseções antigas do AIA, o DOM ao vivo trouxe texto adicional junto de “Concluído”. O coletor também só verifica abertura dos primeiros 45 itens e declara todo item AIA fechado por regra fixa.

**Cenário concreto:** o 46º item não recebe `aberto`; a montagem o trata como disponível. Uma nova ambientação reaproveitando o prefixo AIA seria encerrada pelo código mesmo antes de acabar.

**Correção sugerida:** normalização por prefixo/estado estruturado, fila paginada de verificação e data de encerramento proveniente da fonte, nunca do nome da seção.

### MÉDIO 12 — a fila responde “agora”, mas mistura obrigação, material e higiene do AVA

**Fato observado no site:** 34 ações, das quais 19 estavam em “sem prazo definido”. Referências, páginas de início, aprofundamento, fóruns, lives e sínteses aparecem no mesmo nível visual.

`automacao/render.py:368-386` considera a semana encerrada no vencimento normal e ignora o período de carência no cabeçalho. `automacao/enviar_email.py:86-100` volta a chamar avisos antigos de “Chegou novo”.

**Impacto:** ruído esconde a próxima ação de maior valor, especialmente para quem estuda em janelas curtas.

**Correção sugerida:** três listas:

1. **Faça agora** — prazo/nota/bloqueio;
2. **Complete nesta semana** — itens que contam participação;
3. **Materiais e organização** — manual, síntese, referências e itens manuais.

Dentro da carência, mostrar “prazo regular passou; carência até…”.

### MÉDIO 13 — credencial institucional e escrita no repositório estão no mesmo job público

**Arquivo/linhas:** `.github/workflows/guia-diario.yml:8-75`.

**Fato observado:** o helper local envia os segredos por `stdin`, não os imprime, e os logs recentes estavam mascarados. Isso está correto. Porém o job que recebe `AVA_SENHA` também tem `contents: write`, e as Actions são referenciadas por tags (`@v4`, `@v5`), não por SHA imutável.

Secrets do GitHub não são legíveis pela interface, mas qualquer workflow autorizado consegue consumi-los; a frase “nem eu nem ninguém lê o valor” em `automacao/salvar_credenciais.py:8-14` promete mais do que a plataforma garante.

**Correção sugerida:** repositório privado para coleta, artefato sanitizado publicado em repositório Pages separado, Actions fixadas por SHA e permissões divididas por job. Se mantiver o desenho atual, proteger mudanças de workflow e revisar colaboradores.

### BAIXO 14 — legado e cache sem poda aumentam a manutenção

**Fato observado:** `capturar_sessao.py` e `publicar_sessao_no_github.py` pertencem ao fluxo antigo. `renovar_sessao.py/.bat` ainda é citado pelo site/e-mail, portanto não pode ser removido antes de atualizar essas instruções. `.github/workflows/guia-diario.yml:30-41` ainda restaura `AVA_STORAGE_STATE`.

`docs/estado.json` não remove discussões antigas; `automacao/coletar.py:617-623` só filtra a saída.

**Correção sugerida:** remover `capturar_sessao.py`, `publicar_sessao_no_github.py` e o Secret antigo após trocar as mensagens de recuperação. Manter `renovar_sessao` apenas se houver um caso manual desejado. Podar cache por curso ativo e último acesso, com backup.

## 5. Decisões de projeto que eu contestaria

| Decisão | Parecer |
|---|---|
| Prazo nunca é estimado | **Concordo com a regra; a implementação a viola.** Hora padrão e propagação devem ser removidas do campo `prazo`. |
| Abertura não é prazo | **Concordo.** Exigir tokens inteiros e representar evento de abertura separadamente; hoje “inicial” casa com “inicia”. |
| Item encerrado sai da fila | **Concordo com ressalva.** Só depois de confirmação estruturada; ausência de frase não prova que está aberto. |
| Seção bloqueada com prazo vira alerta | **Concordo com o alerta, não com o prazo copiado.** Mostrar a obrigação bloqueada e sua fonte sem inventar prazo para cada item. |
| Urgência sobe pela cadeia | **Contesto o desenho atual.** A prioridade pode subir; o prazo do predecessor não. A cadeia precisa vir da condição real do AVA. |
| Avisos em cache por 45 dias | **A duração é aceitável.** O problema é guardar dez posts genéricos, não eventos oficiais resolvidos. |
| Privacidade com 400 caracteres | **Contesto fortemente.** Truncamento não é anonimização; nomes, telefone e relato pessoal continuam pessoais. |
| Descoberta automática de disciplinas | **Concordo com guardas.** Filtrar cursos ativos, medir queda anormal e reservar orçamento por curso. |

## 6. Melhorias propostas, priorizadas

| Prioridade | Melhoria | Esforço estimado | Ganho esperado |
|---|---|---:|---|
| P0 | Contrato de saúde, preservação do último sucesso e status por fonte | 4–8 h | Elimina o “tudo em dia” falso |
| P0 | Remover corpos/nomes de alunos do público e separar coleta privada de publicação | 1–2 dias | Reduz drasticamente risco de privacidade |
| P0 | Modelo estruturado de obrigação com múltiplas fases | 1–2 dias | Captura submissão + revisão por pares sem ambiguidade |
| P0 | Trocar prazo propagado por prioridade herdada baseada em grafo real | 4–8 h | Evita prazo inventado |
| P1 | Testes com fixtures HTML reais sanitizadas e casos de datas | 1–2 dias | Protege contra regressões de DOM e calendário |
| P1 | Leitor de item: abertura, fechamento, submissão, tentativas e fases | 1 dia | Cria redundância quando calendário/fórum falha |
| P1 | União calendário API + DOM + ICS, com cobertura e deduplicação | 1 dia | Reduz omissões de eventos |
| P1 | Pipeline de fóruns por papel do autor e prioridade de fonte | 1 dia | Menos ruído, mais chance de achar aviso válido |
| P1 | Retry/backoff, timeout e heartbeat externo | 4–8 h | Falha visível e recuperável |
| P1 | Calendário oficial de provas presenciais | 4–8 h | Evita a obrigação de maior peso ficar fora |
| P2 | Gradebook e feedback privados, com alerta de erro/nota ausente | 1 dia | Detecta o erro atual da COM170 e pendências de feedback |
| P2 | Agrupar “sem prazo” e destacar apenas nota/prazo nas primeiras posições | 2–4 h | Resposta mais clara para estudo em intervalos curtos |
| P2 | Previsão de participação/nota com confiança e fonte | 1–2 dias | Permite decidir onde investir tempo |
| P2 | Histórico de conclusões e gráfico semanal | 1 dia | Mostra evolução sem depender do estado atual do Moodle |
| P3 | Limpeza do legado e poda do cache | 2–4 h | Menor custo de manutenção |

### Matriz mínima de testes recomendada

1. Datas: `26/07`, `26 de julho`, `01 ago. 2026`, `1º de agosto`, sem hora, com hora, dezembro → janeiro.
2. Texto: abertura e fechamento na mesma frase; “live inicial”; data histórica; dois prazos no mesmo módulo.
3. Calendário: 0, 1, 49, 50 e 51 eventos; API parcial; evento sem `cmid`.
4. Fórum: discussão única, tópicos separados, post editado, datas iguais, mais de dez posts relevantes, autor institucional e aluno.
5. DOM: zero cursos, curso sem seções, subseção duplicada, status com texto extra, idioma alterado.
6. Ação: submissão + revisão, dependência explícita, módulo numerado sem dependência e item opcional na mesma seção.
7. Privacidade: telefone, e-mail, CPF, link de WhatsApp e nome de aluno nunca aparecem no artefato público.

## 7. O que foi verificado e estava correto

- A filtragem `closest(...) === seção` em `automacao/coletar.py:145-147` evita contar a subseção duas vezes.
- Os nomes das atividades vêm de `data-activityname`, e os tipos Moodle foram lidos corretamente.
- O link do cronograma regular foi descoberto no curso e corresponde ao cronograma oficial 2026.3.
- As datas do cronograma atual foram interpretadas corretamente, inclusive carência.
- O teto de 50 do calendário foi respeitado; no estado atual, os três eventos da API coincidiram com os três eventos ao vivo.
- A separação explícita de “Abertura das submissões” e “Fechamento das submissões” funcionou para o aviso atual.
- O login em duas telas funcionou no último run; o log não revelou usuário ou senha.
- `salvar_credenciais.py` usa `getpass` e envia o segredo ao GitHub por `stdin`.
- O site escapa conteúdo textual antes de gerar HTML e usa `rel="noopener"` nos links.
- A fila atual identificou corretamente como pendentes os quizzes de COM100, SOC100 e COM170; o quiz LET110 ainda estava marcado manualmente como não concluído.
- O prazo de 26/07 do Módulo 4 e a dependência real do quiz M1 foram confirmados no aviso e no AVA.
- Os prazos regulares de 29/07, a carência de 02/08 e o fechamento dos quizzes em 02/08 correspondem às fontes oficiais atuais.
- O caminho `session_expired` mantém o retrato anterior, mostra banner e faz o workflow terminar com erro.
- `concurrency.cancel-in-progress: false` evita que dois runs do próprio robô se cancelem.
- O arquivo local de sessão é removido no runner com `if: always()`.

## 8. Conclusão

O projeto tem uma base boa e já corrige erros reais do protótipo anterior. O problema não é a intenção das decisões, e sim a falta de um **modelo explícito de evidência e cobertura**. Hoje, “prazo”, “prioridade”, “evento”, “fase”, “fonte” e “confiança” estão misturados no mesmo objeto. Enquanto isso não for separado, a automação continuará vulnerável às duas falhas que ela mais precisa evitar: omitir obrigação e transformar inferência em prazo oficial.

Os quatro itens P0 devem ser tratados antes de novas funções de previsão de nota ou histórico.
