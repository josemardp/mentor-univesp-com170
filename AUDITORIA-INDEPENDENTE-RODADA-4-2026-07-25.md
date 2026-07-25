# Auditoria independente — rodada 4

**Data:** 25/07/2026  
**Alvos:** site/e-mail publicados, AVA ao vivo, commit `f8cebe9` e workflow
`guia-diario.yml`  
**Método:** reconciliação direta com a sessão autenticada do AVA, inspeção do
site público, testes locais, histórico da Action e injeção controlada de falhas.

## 1. Resumo executivo

O robô captura as quatro disciplinas, os três prazos explícitos do calendário e
os três prazos críticos do aviso da COM170. A suíte local continua verde.
Ainda assim, a resposta central do produto estava errada no primeiro confronto:
o site mandava fazer um quiz que o AVA já marcava como concluído e não mostrava
as quatro pendências já liberadas no Módulo 2. Uma execução manual posterior
atualizou corretamente o site, confirmando que o defeito é de frescor, não do
parser. Além disso, as três fontes de prazo podem desaparecer simultaneamente e
a coleta continuar com `status: ok`; falha de e-mail também termina com sucesso.
O veredito é **não confiável para uso desacompanhado**: o caminho feliz funciona,
mas frescor e detecção de silêncio ainda não protegem contra omissão.

---

## 2. Escopo e separação dos alvos

Durante a auditoria houve uma alteração concorrente legítima: o trabalho da
rodada 3 foi consolidado no commit `f8cebe9`. Não editei nem reverti esse
trabalho.

Há duas fotografias distintas:

| Alvo | Estado observado |
|---|---|
| Site público no primeiro confronto | Última leitura indicada: **25/07 às 18:47 (Brasília)**; mostrava o quiz do Módulo 1 como primeira ação |
| AVA ao vivo | Módulo 1 inteiro concluído; Módulo 2 aberto, com duas atividades concluídas e quatro pendentes |
| Commit `f8cebe9` | Suíte local verde; contém as correções da rodada 3 e separa higiene/conferência |
| Action do commit `f8cebe9` | Disparo manual `30177371861` concluído com sucesso às 19:22; coletou 4 cursos, 36 seções e 62 itens |
| Site público após o disparo | Última leitura **19:21**; primeira ação mudou para `M2 - Material-base`, coerente com o novo retrato |

Não foram reapresentados como novos os achados já corrigidos nas três rodadas
anteriores. Também não foram reabertos os temas adiados de boletim, previsão de
nota, prova presencial ou a decisão de privacidade já aceita.

---

## 3. Teste da decisão real

Pergunta operacional: **“Se Josemar tiver 40 minutos agora, o produto aponta a
ação certa?”**

**Resultado: falhou.**

| Evidência | Site público | AVA ao vivo |
|---|---|---|
| COM170 · Módulo 1 | Quiz `173832` pendente e primeira ação | Os cinco itens estavam `Concluído`, inclusive `173832` |
| COM170 · Módulo 2 | Não aparece; o recado diz que está bloqueado | Módulo aberto |
| Estado do Módulo 2 | Ausente | `173834` e `173835` concluídos; `173836`, `173837`, `173838` e `173839` pendentes |
| Decisão resultante | Tentar refazer atividade concluída | Começar por `173836`, a próxima atividade pendente |

Uma execução manual iniciada durante a auditoria terminou às 19:22, gerou um
retrato com 62 itens e alterou a primeira ação pública para
`M2 - Material-base`. Isso confirma que o parser acompanhou o avanço assim que
foi chamado.

O problema é o contrato de frescor. O produto é usado em dois momentos
diferentes: o e-mail é um retrato diário, mas o site é aberto quando o estudo
começa. Um site estático sem atualização sob demanda não consegue cumprir a
promessa “o que fazer agora” depois que o aluno avança no AVA; nesta auditoria,
foi necessário um disparo manual para corrigir a decisão.

No celular, o teste de dez segundos já havia falhado na rodada 3 porque o recado
da mentora ocupa a primeira tela. Nesta rodada ele falha também pelo conteúdo:
mesmo após rolar, a primeira ação está obsoleta.

---

## 4. Inventário reconciliado: AVA × robô

| Informação/obrigação | Fonte verificada no AVA | Captura atual | Veredito e impacto |
|---|---|---|---|
| Quatro disciplinas e estrutura semanal/modular | Páginas dos cursos `18870`, `18880`, `18893` e `18922` | Sim | **Correto.** Foram lidas 4 disciplinas, 36 seções e 56 itens no retrato publicado |
| Conclusão de itens COM170 | Página do curso `18922` | Sim, somente no momento da coleta | **Parcial.** O parser lê, mas o produto ficou obsoleto após o aluno concluir M1 |
| Próximas atividades do Módulo 2 | Página do curso `18922` | Não no retrato de 18:47; sim após a coleta de 19:21 | **Omissão temporária.** Quatro atividades ficaram fora da decisão até o disparo manual |
| Módulo 4 até 26/07 | Aviso do facilitador, discussão `124738` | Sim | **Correto.** Prazo e origem concordam |
| Trabalho em grupo até 01/08 | Mesmo aviso | Sim | **Correto.** A fase de submissão é separada |
| Avaliação por pares até 04/08 | Mesmo aviso | Sim | **Correto.** A segunda fase não foi perdida |
| Quizzes S1 de COM100, LET110 e SOC100 | Calendário e páginas dos quizzes | Sim | **Correto.** Fechamento em 02/08 às 23:59 nos três |
| Vencimento nominal da Semana 1 | Cronograma regular oficial | Sim | **Correto como prazo semanal:** 29/07 às 23:59, carência até 02/08 |
| Videoaulas e materiais regulares contam para participação | Critério publicado pelo facilitador + conclusão manual nos itens | Sim, por heurística de rótulo | **Parcial.** A conclusão contribui para a participação, mas a origem dessa classificação não é guardada por item |
| Prazo de 29/07 aplicado a cada vídeo/texto | Cronograma diz “vencimento das atividades”; páginas individuais não exibem data | Sim | **Inferência não explicitada.** Não é uma data inventada, mas a união “item avaliativo + semana” deveria aparecer como regra derivada, não como prazo direto do item |
| Quizzes/SCORM do Módulo 2 | Páginas `173838` e `173839` | Sim quando o módulo está aberto | **Parcial.** Há nota/tentativas, mas não há prazo próprio na página |
| Peso dos filhos de cada módulo COM170 | Critério diz que a **conclusão do módulo** é uma atividade contável | Cada filho recebe “vale nota” | **Impreciso.** O filho contribui para concluir o módulo, mas a fonte não diz que cada filho possui nota atômica |
| Live COM170 | Critério da disciplina diz uma live por quinzena | Sim, sem prazo | **Correto quanto à relevância;** presença/visualização não foi confirmada |
| Fóruns e avisos | Páginas de discussão | Sim, com cache e corte | **Parcial.** Encontrou o aviso crítico real, porém perda da fonte não afeta a saúde |
| Notificações | API do Moodle | Sim, metadado | **Correto para avisos de abertura;** não vira obrigação por si só |
| Mensagens privadas | API do Moodle | Só metadado | **Correto dentro da decisão de privacidade** |
| Idade de cada fonte | Não é dado do AVA; é telemetria do coletor | Não | **Ausente.** O usuário vê a hora global, não sabe se fórum/calendário/cronograma vieram de cache ou falharam |
| Divergência entre fontes | Calendário, cronograma, aviso e página do item | Não modelada | **Ausente.** O robô escolhe/combina, mas não exibe conflito ou grau de confiança por campo |

### Contradição na própria fonte

O aviso de avaliação da COM170 afirma “nove atividades contáveis”, mas enumera
dez: quatro módulos, portfólio individual, entrega em grupo, feedback do
portfólio, feedback do grupo, uma live e qualidade da participação. Isso é uma
contradição da fonte, não um bug do robô. Deve ir para “confirmar com o
facilitador”, nunca ser resolvida por inferência do código.

---

## 5. Injeção de falhas e testes de silêncio

Os testes abaixo foram executados contra `f8cebe9`, sem publicar nem alterar
dados do AVA.

| Falha injetada | Resultado observado | Veredito |
|---|---|---|
| Todos os avisos/fóruns vazios | `validar_cobertura()` retornou `(True, [])`; desapareceram M4→26/07, grupo→01/08 e pares→04/08 | **Falha crítica e silenciosa** |
| Cronograma ausente | Saúde continuou verde | **Falha silenciosa** |
| Calendário ausente | Saúde continuou verde | **Falha silenciosa;** não existe contrato mínimo da fonte |
| Avisos + cronograma + calendário ausentes, e prazos derivados zerados | `health=True`, `problems=[]`, 14 ações, **zero prazo confirmado** | **Falha crítica:** o robô pode ficar sem todos os prazos e declarar sucesso |
| SMTP lança `OSError("smtp fora")` | Imprimiu `Falhei ao enviar o e-mail: smtp fora` e retornou **0** | **Falha silenciosa e Action verde** |
| Item repetido com mesmo rótulo em duas seções | `novidades()` usa `(curso, label)` e colide | **Falha condicional:** não ocorreu nos rótulos atuais, mas a identidade não é estável |
| JSON truncado/corrompido | `carregar()` devolve o padrão sem registrar corrupção | **Falha silenciosa condicionada a escrita interrompida** |

O calendário ao vivo tinha apenas três eventos, portanto o teto de 50 não
causou perda hoje. A ausência de paginação continua sendo um risco
**condicional**, não uma perda observada nesta data.

---

## 6. Achados novos, por severidade

### Crítico 1 — saúde valida o curso, mas não valida nenhuma fonte de prazo

**Arquivos/linhas:** `automacao/coletar.py:1376-1422`,
`automacao/coletar.py:1425-1437`.

**Fato reproduzido**

Entrada: quatro cursos, seções e itens válidos; avisos, calendário e cronograma
vazios; prazos derivados zerados.

Saída: `validar_cobertura() → (True, [])`, 14 ações e zero prazo confirmado.

O resumo conta as fontes, mas a contagem não participa do contrato de saúde.
Logo, “o Moodle abriu” mascara “as fontes que contêm os prazos falharam”.

**Correção sugerida**

Criar contratos independentes por fonte, com estado
`ok/vazio_esperado/falhou/cache`, idade, quantidade atual e faixa histórica.
Para uma fonte obrigatória, falha ou queda anormal deve produzir
`coleta_incompleta`; para uma fonte opcional, deve manter as demais e exibir
degradação explícita.

### Crítico 2 — o site aponta uma ação já concluída e omite a próxima

**Arquivos/linhas:** arquitetura de atualização em
`.github/workflows/guia-diario.yml:5`, consumo do retrato em
`automacao/render.py:490`.

**Fato observado**

Site às 18:47: quiz M1 é a primeira ação e M2 está bloqueado.  
AVA ao vivo: M1 inteiro concluído; M2 aberto com quatro pendências.

Depois de uma execução manual às 19:21, o site mudou a primeira ação para M2.
Portanto, o caso isola a causa: **frescor insuficiente**, e não falha de leitura
do DOM.

**Correção sugerida**

Manter o e-mail como fotografia diária, mas oferecer no site um botão simples
“Atualizar agora”, com horário e resultado por fonte. Enquanto a atualização
não existir, a interface deve dizer “retrato de 18:47; confirme no AVA se você
estudou depois disso” e não usar linguagem presente como “faça agora”.

### Alto 3 — indisponibilidade do e-mail é declarada sucesso

**Arquivos/linhas:** `automacao/enviar_email.py:208-238`,
`.github/workflows/guia-diario.yml:62-70`.

**Fato reproduzido**

`SMTP()` levantou `OSError("smtp fora")`; `main()` retornou 0. O workflow ainda
usa `continue-on-error: true`, portanto há duas camadas convertendo falha em
verde.

**Correção sugerida**

O script deve retornar código diferente de zero. Se o site puder ser publicado
mesmo assim, usar `continue-on-error` somente para prosseguir e adicionar um
passo final que falhe/alerte especificamente por canal. O estado publicado deve
registrar “site atualizado; e-mail não entregue”.

### Alto 4 — não há heartbeat externo e o agendamento ainda não foi provado

**Arquivo/linha:** `.github/workflows/guia-diario.yml:5`.

**Fato observado**

Os históricos consultados em 25/07 eram todos `workflow_dispatch`. Não havia
uma sequência de execuções pelo evento `schedule`, nem monitor fora do próprio
GitHub. Se o cron deixar de disparar, nenhum código do job chega a rodar para
avisar.

**Correção sugerida**

Heartbeat externo com prazo máximo de chegada, por exemplo até 08:20 de
Brasília, e alarme independente. Considerar o agendamento aceito somente após
sete disparos `schedule` consecutivos.

### Alto 5 — semântica de “vale nota” não preserva a fonte nem a granularidade

**Arquivo/linhas:** `automacao/coletar.py:893-904`,
`automacao/coletar.py:1238-1243`.

**Fato observado**

Em disciplinas regulares, o aviso sustenta que vídeo, material e quiz compõem a
participação. Porém `conta_nota()` reconstitui isso apenas por tipo/rótulo, sem
guardar o aviso que justifica a decisão. Na COM170, a fonte pontua conclusão do
módulo, enquanto cada filho do módulo recebe o selo “vale nota”.

**Saída problemática**

O site apresenta uma conclusão forte e atômica sem permitir responder “qual
fonte disse que este item vale nota?”.

**Correção sugerida**

Substituir o booleano por:

- `avaliacao: direta | requisito | participa_do_componente | não_avaliativa`;
- `avaliacao_fonte` e `avaliacao_fonte_url`;
- `regra_derivada`, quando houver união entre critério do curso e semana.

### Médio 6 — o fallback de cronograma faz a telemetria afirmar uma fonte que o curso não forneceu

**Arquivos/linhas:** `automacao/coletar.py:45`,
`automacao/coletar.py:1027-1031`, `automacao/coletar.py:1436`.

**Fato observado**

Todo curso sem link recebe `CRONOGRAMA_PADRAO`, inclusive COM170, que usa modelo
quinzenal. O resumo publicado contou cronograma para quatro cursos.

**Impacto**

Hoje o fallback não atribuiu semanas regulares à COM170, mas o diagnóstico
“cronograma: 4” é falso e esconde a ausência da fonte específica.

**Correção sugerida**

Só aceitar fallback em curso reconhecido como regular e registrar
`descoberto_no_curso` versus `fallback`. COM170 deve ficar como
`não_aplicável`, não como quarta captura bem-sucedida.

### Médio 7 — publicação não é uma transação entre coleta, e-mail, Git e Pages

**Arquivo/linhas:** `.github/workflows/guia-diario.yml:62-86`.

**Fato observado**

O e-mail é enviado antes de `git push`, e o job não verifica o deploy do Pages.
Se o push ou o Pages falhar depois do SMTP, o usuário recebe um e-mail novo
apontando para um site antigo.

**Correção sugerida**

Publicar, confirmar o commit/deploy, então enviar o e-mail com o mesmo
`snapshot_id`. Em caso de degradação intencional, ambos os canais devem mostrar
esse ID e o estado da fonte.

### Médio 8 — arquivos de estado e saída não são escritos atomicamente

**Arquivos/linhas:** `automacao/coletar.py:1440-1446`,
`automacao/coletar.py:1481`, `1497`, `1514-1515`;
`automacao/render.py:490`.

**Fato do código**

`write_text()` grava diretamente os JSONs e o HTML. Se houver interrupção,
`carregar()` captura qualquer exceção e retorna o padrão, sem distinguir arquivo
ausente de arquivo corrompido.

**Cenário reproduzível**

JSON truncado → `carregar()` devolve `None/{}` → o contexto anterior usado na
saúde ou no cache desaparece sem diagnóstico.

**Correção sugerida**

Escrever em arquivo temporário no mesmo volume, validar JSON/HTML, `fsync` quando
aplicável e substituir atomicamente. Corrupção deve gerar erro explícito e
preservar backup do último snapshot válido.

### Médio 9 — identidade de item e novidade depende do texto visível

**Arquivo/linhas:** `automacao/coletar.py:1449-1463`.

**Fato reproduzido**

Dois itens com o mesmo rótulo em seções diferentes colidem porque a chave é
`(curso, label)`. O `cmid`, já disponível, não participa da identidade e nem é
levado às ações.

**Correção sugerida**

Usar `(course_id, cmid)`; para entidades sem `cmid`, usar o ID real do Moodle.
Rótulo deve ser apresentação, não chave.

### Baixo 10 — calendário tem teto de 50 sem paginação

**Arquivo/linhas:** `automacao/coletar.py:595-600`.

**Condição**

Hoje havia três eventos e não houve perda. Se a janela passar de 50, a API pode
entregar apenas a primeira página; o DOM só é usado como plano B, não como
união/validação.

**Correção sugerida**

Paginar por faixa de tempo ou usar cursor suportado, guardar cardinalidade e
comparar API × DOM.

---

## 7. Critérios de aceite da rodada 4

| Critério | Resultado | Evidência |
|---|---|---|
| Nenhum prazo inventado | **Não demonstrado** | Datas críticas observadas estão corretas, mas a aplicação do prazo semanal a cada recurso é uma regra derivada não explicitada |
| Nenhuma obrigação relevante omitida nos próximos 14 dias | **Falhou no primeiro retrato** | Quatro pendências do M2 ficaram ausentes até o disparo manual; perda dos avisos apaga três prazos COM170 mantendo saúde verde |
| Todo “vale nota” possui fonte rastreável | **Falhou** | O dado final contém booleano, não a origem por item |
| Divergência entre fontes é visível | **Falhou** | Não há modelo de divergência |
| Uma fonte pode falhar isoladamente sem derrubar as outras, mas com aviso | **Falhou** | Isolamento existe, visibilidade/estado não |
| Idade de cada fonte é visível | **Falhou** | Só existe `checked_at` global |
| Falha de execução é detectada externamente | **Falhou** | Não há heartbeat externo |
| Sete agendamentos reais consecutivos | **Não verificável** | Histórico consultado só tinha execuções manuais |
| Próxima ação aparece na primeira tela móvel | **Falhou** | Recado vem antes; a ação exibida também estava obsoleta |
| E-mail reduzido a até cinco linhas decisórias | **Falhou** | O produto publicado ainda traz lista longa e novidades |
| Suíte do commit auditado está verde | **Passou** | `test_prazos.py` e `test_login.py` passaram localmente; testes do workflow também passaram |

---

## 8. Cobertura de testes: o que falta

A suíte protege as correções anteriores, mas ainda é majoritariamente unitária.
Casos mínimos novos:

1. `avisos=[]`, calendário ausente e cronograma ausente devem tornar a coleta
   incompleta, mesmo com quatro cursos íntegros.
2. Queda de cada fonte isolada deve aparecer em `fontes_status`, com idade e
   motivo.
3. SMTP indisponível deve devolver código não zero e o passo final deve
   distinguir site publicado de e-mail não entregue.
4. Dois itens com mesmo rótulo e `cmid` diferentes devem gerar duas novidades.
5. Interrupção entre arquivo temporário e substituição deve preservar o snapshot
   anterior.
6. E2E com sequência: coleta A → aluno conclui M1 → coleta B → a primeira ação
   passa para M2.
7. Contrato de render: item `requisito` não pode receber texto “vale nota
   diretamente”.
8. Workflow: push falha depois da coleta; nenhum e-mail deve anunciar um
   snapshot que não foi publicado.
9. Workflow agendado: teste/monitor verifica ausência de heartbeat até o horário
   limite.

---

## 9. Prioridade de correção

| Ordem | Mudança | Esforço | Ganho |
|---|---|---:|---|
| 1 | Contrato e telemetria por fonte, falhando fechado para perda de prazos | Médio | Elimina a maior omissão silenciosa |
| 2 | Atualização sob demanda do site + aviso explícito de frescor | Médio/alto | Faz a próxima ação refletir o estudo real |
| 3 | Heartbeat externo e falha real do canal de e-mail | Baixo/médio | Detecta robô parado ou canal quebrado |
| 4 | Taxonomia avaliativa com fonte e regra derivada | Médio | Evita afirmações fortes sem rastreabilidade |
| 5 | Publicação transacional com `snapshot_id` | Médio | Mantém site e e-mail coerentes |
| 6 | Escrita atômica e IDs estáveis | Baixo/médio | Reduz corrupção e colisões futuras |
| 7 | Paginação/união do calendário | Baixo | Previne perda quando o volume crescer |

---

## 10. O que foi verificado e estava correto

- A sessão autenticada permitiu ler o AVA sem solicitar ou manipular senha.
- As quatro disciplinas esperadas estavam acessíveis.
- O parser de estrutura continua capturando cursos, seções, itens e bloqueios.
- O Módulo 1 da COM170 foi corretamente reconhecido como concluído no AVA ao
  vivo; a divergência estava no retrato publicado, não no DOM atual.
- O aviso real sustenta M4 em 26/07, entrega em grupo em 01/08 e avaliação por
  pares em 04/08; o robô preservou as três fases.
- O calendário sustentou os três quizzes regulares em 02/08 às 23:59.
- O cronograma oficial sustentou vencimento nominal da Semana 1 em 29/07 às
  23:59 e carência até 02/08.
- A data de abertura não foi promovida a prazo.
- A prioridade herdada continua distinta de prazo próprio.
- As correções da rodada 3 estão presentes em `f8cebe9`: prazo duvidoso vai para
  conferência; higiene sai da fila principal; identidade de deduplicação de fase
  usa o rótulo inteiro.
- Os testes locais de prazo e login passaram.
- A Action manual `30177371861` terminou verde: 19 ações, 18 itens de higiene,
  6 pontos a confirmar e 0 encerrados; o e-mail real foi enviado e o commit de
  dados `a0d649f` foi criado.
- O Pages passou a servir a leitura das 19:21 e incluiu o Módulo 2; isso
  confirmou o caminho feliz de coleta, publicação e renderização.
- Não havia mais de 50 eventos de calendário no cenário atual.
- Nenhum arquivo do produto foi alterado nesta auditoria; somente este relatório
  foi criado.

## 11. Limitações declaradas

- Não forcei falha real no AVA, no SMTP, no GitHub Pages ou no repositório; as
  falhas foram injetadas localmente ou inferidas da ordem explícita do workflow.
- Não enviei e-mail real.
- Não havia sete execuções agendadas para observar.
- O teste cognitivo de dez segundos foi feito sobre os artefatos, não como
  entrevista falada com Josemar.
- Não reauditei boletim, prova presencial, previsão de nota nem a decisão de
  publicar trechos de fórum, conforme o escopo já decidido.
