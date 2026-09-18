# Auditoria independente — rodada 2

**Data:** 25/07/2026  
**Revisão auditada:** `16c5a23`  
**Escopo:** código local, dados persistidos, site renderizado, 61 verificações automatizadas e sessão autenticada do AVA.

## 1. Veredito das correções da rodada 1

| Correção | Veredito | Evidência |
|---|---|---|
| Falhar fechado em coleta incompleta | **Segura com ressalva** | `validar_cobertura()` recusa zero curso, curso sem seção e curso sem item; `coletar.main()` preserva o retrato anterior, grava `coleta_incompleta` e retorna 2 (`automacao/coletar.py:1180-1210, 1275-1289`). A Action fica vermelha porque o passo “Gerar guia” recebe esse código. A ressalva é dupla: 4→3 e 4→2 passam, e o retorno 2 interrompe o job antes de renderizar, enviar e-mail, publicar e executar a verificação explícita. Portanto, o repositório não é sobrescrito por uma coleta ruim, mas o site público também não recebe o aviso prometido. |
| Escopo de aviso e uma ação por fase | **Não segura** | O caso atual de COM170 melhorou: há ações distintas para entrega em 01/08 e avaliação por pares em 04/08. Porém, o escopo nunca é encerrado (`automacao/coletar.py:409-413`) e o dedup `(quando, verbo)` elimina obrigações diferentes (`automacao/coletar.py:1030-1033`). Ambos foram quebrados com entradas reproduzíveis na seção 3. |
| Dependência real e herança somente de prioridade | **Segura com ressalva** | No AVA real, M2←M1, M3←M2, M4←M3 foi seguido corretamente e o quiz M1 recebeu `prioridade_ate=26/07`, mantendo `prazo=None`. O site diz “faça antes de”, não “vence” (`automacao/coletar.py:1163-1176`; `automacao/render.py:129-135`). Se o prefixo do predecessor mudar, a propagação para — mas falha por omissão de prioridade, não por invenção de prazo. |
| Parser de horário, ordinal, ano e abertura/fechamento | **Não segura** | As correções específicas funcionam: `1º de agosto`, hora ausente marcada como incerta, hora explícita e virada dezembro→janeiro passaram. Contudo, duas datas na mesma frase recebem o mesmo tipo, e “abre ... fecha ...” sem outra palavra de prazo nem sequer passa pelo pré-filtro. Um aviso republicado suficientemente tarde também pode avançar o ano indevidamente. Cenários na seção 3. |
| Hardening pós-deploy: duplicata idêntica, verbo pelo rótulo e testes antes do AVA | **Segura com ressalva** | O aviso repetido em dois fóruns gera uma obrigação, “Fechamento das submissões” vira **Entregue** e “avaliações por pares” vira **Avalie**. As 49 verificações de prazo e 12 de login passaram, e a Action as executa antes do AVA (`.github/workflows/guia-diario.yml:30-35`). O dedup, porém, é amplo demais para obrigações distintas, e a suíte atual prova apenas a duplicata idêntica. |

**Conclusão principal:** as correções reduziram de forma real o risco de prazo inventado, mas duas das cinco ainda não podem ser consideradas fechadas. O maior ganho confirmado é a prioridade herdada sem prazo falso. As duas brechas mais perigosas são omissão de curso no contrato de saúde e colapso de obrigações distintas no dedup de fases.

## 2. Regressões encontradas

### 2.1 Cache antigo não é migrado

**Fato observado:** `docs/estado.json` contém 44 objetos de prazo; 16 não têm `hora_certa` nem `escopo`, embora tenham `tipo`. Eles foram produzidos pelo extrator anterior. Quando uma discussão não recebe post novo, `varrer_foruns()` devolve o cache diretamente, sem chamar `_preparar()` novamente (`automacao/coletar.py:668-674, 679-683`).

**Impacto atual observado:** a inconsistência existe no arquivo de produção, mas não encontrei uma ação visível errada causada somente por ela. O aviso novo/repetido da Q1 foi reprocessado e hoje fornece os prazos corretos que chegam à fila.

**Conclusão:** regressão de dados confirmada, efeito visível atual neutralizado por acaso. Uma versão de esquema no cache ou reprocessamento obrigatório após mudança do extrator é necessária.

### 2.2 Ações anteriores não desapareceram legitimamente

Comparação do retrato anterior (`cc1b5fb`, 34 ações) com o atual (35):

- o quiz M1 deixou de ter prazo inventado e passou a ter prioridade;
- “Destrave e entregue Módulo 4” foi substituído pela obrigação real do aviso;
- Módulo 6 passou de uma obrigação genérica para duas fases, entrega e avaliação.

Não encontrei uma ação legítima que tenha sumido por causa da retirada do prazo de aviso dos itens. Prazos próprios de quiz continuam vindo do calendário por `cmid`; videoaulas e materiais-base regulares continuam usando o cronograma oficial.

### 2.3 `encerrados=0` não prova que a detecção de encerramento funciona

**Fato observado:** o AVA tem tarefas encerradas no AIA. A S2 terminou em 05/07 e o workshop S4 mostra submissões fechadas em 15/07, avaliações fechadas em 16/07 e “o prazo de envio terminou”. Mesmo assim, o retrato tem zero encerrados.

Isso ocorre porque as subseções do AIA não chegam como seções com itens no `data.json`; a seção-pai aparece vazia e depois é removida dos cards (`automacao/render.py:354-362`). Para o produto atual, esconder o AIA encerrado é uma decisão aceitável. Para a métrica de saúde, porém, zero significa “não observei encerrados no subconjunto coletado”, não “o detector reconheceu corretamente todos os encerrados”.

### 2.4 As 19 ações sem prazo não são 19 perdas de prazo

**Fato observado:** 18 são páginas, fóruns, referências e lives regulares que não contam nota segundo os critérios publicados. Uma é materialmente diferente: **Live com facilitador da COM170**, marcada como `conta_nota=True`; o aviso real diz que a live inicial ocorreu em 23/07 e que a gravação deve ser vista.

Não encontrei fonte oficial atribuindo um vencimento próprio à gravação. Logo, não seria correto inventar prazo. O defeito é de apresentação/cobertura: uma obrigação que vale nota está misturada com 18 itens de higiene e perdeu o vínculo com o aviso de 23/07.

## 3. Ataque às oito heurísticas

### 3.1 `secao_do_predecessor()` — **quebra em condição X**

- `M3 - O custo invisível...` + seções `Módulo 3`/`Semana 3` → **Módulo 3**, correto.
- `M03 - ...` → **Módulo 3**, correto.
- `Atividade M3 - ...` ou `Quiz M3 - ...` → `None`.

No AVA atual, os predecessores intermediários começam exatamente por M1/M2/M3, então não quebrei o dado de produção. Quebra se o Moodle/facilitador acrescentar uma palavra antes do prefixo ou se o rótulo não começar pela família da seção. A consequência é não herdar prioridade; não há prazo inventado.

### 3.2 Escopo carregado adiante — **quebrei**

Entrada:

```text
Módulo 4: o trabalho precisa ser entregue até 26/07.
LIVE MAGNA: será realizada em 30/07.
Prova presencial: acontece em 10/09.
```

Saída de `extrair_prazos()`/`casar_prazos("Módulo 4")`: três prazos para Módulo 4 — 26/07, 30/07 e 10/09. O escopo de Módulo 4 continua anexado à live e à prova porque não há reset sem um novo “Módulo N” (`automacao/coletar.py:409-413, 969-971`).

O aviso real atual já muda de “Módulo 6 e 7” para “LIVE INICIAL” sem novo escopo. Hoje a live é filtrada como abertura, portanto não cria a ação falsa. A estrutura perigosa já existe no texto real; basta a próxima live usar “acontece”/“será realizada”.

### 3.3 Limiar de cobertura — **quebrei**

Com retrato anterior de quatro cursos, resultados reais da função:

| Nova coleta | Resultado |
|---|---|
| 4 cursos | aceita |
| 3 cursos | aceita |
| 2 cursos | aceita |
| 1 curso | recusa |
| 0 cursos | recusa |

O comparador é `< len(antes) / 2`, não `<=` (`automacao/coletar.py:1196-1199`). Assim, perder uma disciplina — ou até metade delas — pode ser publicado silenciosamente. No fim do bimestre, a regra inversa também é pobre: ela não sabe distinguir transição oficial de falha de DOM. O contrato precisa acompanhar IDs de cursos e um sinal de período, não apenas quantidade.

### 3.4 Dedup `(quando, verbo)` — **quebrei**

Entrada em Módulo 6, ambas às 01/08 23:59:

- “Fechamento da submissão individual” → **Entregue**;
- “Fechamento da submissão do grupo” → **Entregue**.

Saída: uma ação, a individual. A segunda some em `automacao/coletar.py:1030-1033`.

O cenário é academicamente realista e está apoiado pelo aviso oficial de critérios da COM170, que lista separadamente “Entrega individual do portfólio” e “Entrega de grupo”. Ainda não há, no AVA atual, datas confirmadas iguais para ambas; a falha do algoritmo está confirmada, a ocorrência em produção ainda é hipótese.

### 3.5 Rótulo de 55 caracteres — **quebra em condição X**

“Fechamento das submissões” (25 caracteres) permanece intacto.  
“Fechamento da submissão individual do relatório técnico revisado e assinado pela equipe” (87) vira apenas **entrega**.

Não causa perda interna de prazo, mas apaga a distinção justamente nos rótulos mais específicos. O limite de 55 é cosmético e não deve decidir preservação semântica. Gravidade baixa isoladamente; combinado ao dedup, dificulta perceber qual obrigação sumiu.

### 3.6 `item_aberto()` pela ausência — **quebrei**

Resultados diretos:

- corpo “Você precisa fazer login para continuar.” → `True`;
- corpo “Você não tem permissão para visualizar esta atividade.” → `True`;
- corpo “O prazo para envio expirou.” → `False`.

Na página real do workshop S4, o AVA usa “Submissões fechadas”, “Avaliações fechadas” e “O prazo de envio terminou”; nenhuma dessas frases está em `SINAIS_FECHADO`. Fora do desvio especial do AIA, essa página seria marcada como aberta (`automacao/coletar.py:717-735`).

### 3.7 Tipo pela ordem das palavras — **quebrei**

Entrada:

```text
A abertura ocorre em 27/07 e o prazo fecha em 01/08.
```

Saída: as duas datas são `inicio`; o fechamento de 01/08 desaparece das ações.  
Outra entrada, “A atividade abre em 27/07 e fecha em 01/08”, produz zero prazo porque `abre`/`fecha` estão na classificação, mas não no pré-filtro `GATILHOS_PRAZO` (`automacao/coletar.py:328-355, 416-419`).

O erro nasce porque `_tipo_prazo()` classifica o fragmento inteiro, não a vizinhança de cada data.

### 3.8 Ano mais próximo do post — **quebra em condição X**

“Relembrando: o prazo foi até 26/07”, sem ano:

- post em 23/07/2026 → 26/07/2026;
- republicado em 20/01/2027 → ainda 26/07/2026;
- republicado em 20/04/2027 → **26/07/2027**.

A heurística funciona para virada curta de ano, mas não para republicação após o ponto médio entre as duas datas candidatas (`automacao/coletar.py:293-305`). O texto real de 24/07/2026 está perto dos prazos e foi resolvido corretamente.

## 4. Achados novos por severidade

### ALTO — o limite de dez posts vale apenas para cinco posts únicos

**Arquivos/linhas:** `automacao/coletar.py:196-211, 639-640, 699-709`.

**Fato observado no dado real:**

- o seletor combina `article.forum-post-container`, `[data-region="post"]` e `.forumpost`;
- no DOM atual, o artigo e um descendente representam o mesmo post;
- o cache corta `posts[:10]` antes da desduplicação final;
- `docs/estado.json` guarda 10 entradas no fórum geral COM100, mas apenas 5 chaves `(data, título, texto)` são únicas;
- o mesmo ocorre em COM100 temático, SOC100 geral, Q1 geral e Q1 dúvidas;
- na leitura autenticada, o fórum geral COM100 tinha 211 posts únicos e 29 passavam pela heurística; o temático tinha 477 e 245 passavam. O cache reteve cinco únicos por discussão.

**Entrada real → saída errada:** 29 posts de interesse no fórum geral COM100 → cinco avisos únicos disponíveis após cache/dedup; 24 são omitidos sem flag.

Não encontrei prazo oficial atual entre os itens omitidos. O aviso da quinzena da COM170 ainda está capturado. Mesmo assim, o risco de omissão é maior do que o achado adiado da rodada 1 indicava, porque o teto efetivo é metade do documentado e fóruns ruidosos substituem posts antigos a cada atualização.

### ALTO — até duas das quatro disciplinas podem sumir sem falhar fechado

**Arquivo/linha:** `automacao/coletar.py:1196-1199`.

**Entrada reproduzível:** retrato anterior com COM100, SOC100, LET110 e COM170; nova coleta com apenas três, ou apenas duas, cada uma ainda contendo seção/item.

**Saída errada:** `(True, [])`; a coleta é publicável como `status=ok`.

Este é um furo direto na correção mais importante. A regra deveria falhar diante da perda inesperada de qualquer ID conhecido durante o período ativo e tratar transição de bimestre por um sinal explícito.

### ALTO — obrigações distintas com mesmo verbo e horário somem

**Arquivo/linha:** `automacao/coletar.py:1022-1033`.

**Entrada reproduzível:** entrega individual e entrega do grupo, mesma seção e horário, ambas classificadas como `Entregue`.

**Saída errada:** uma única ação. O critério oficial da COM170 confirma que essas são categorias acadêmicas distintas; falta apenas ocorrerem com a mesma data para a falha aparecer na produção.

### MÉDIO — falha da coleta não chega ao site nem ao e-mail

**Arquivos/linhas:** `automacao/gerar_guia.py:22-28`; `.github/workflows/guia-diario.yml:52-56, 62-95`.

**Cenário reproduzível:** `coletar.main()` grava `coleta_incompleta` e retorna 2. `gerar_guia.main()` devolve 2 antes de chamar `render.main()`. O passo “Gerar guia” falha e os passos comuns posteriores não executam. A verificação explícita está depois da publicação.

**Saída observável:** Action vermelha e site público antigo, ainda com o último status `ok`; nenhum e-mail de “leitura incompleta”. O dado ruim não é publicado — isso está correto —, mas “site e e-mail avisam” não é verdade no fluxo real.

### MÉDIO — página inacessível ou encerrada pode ser classificada como aberta

**Arquivo/linha:** `automacao/coletar.py:717-735`.

**Entradas reproduzíveis:** página de login, página “sem permissão” e texto real do workshop “Submissões fechadas / prazo terminou”.

**Saída errada:** `True`. Hoje a checagem de AIA mascara o workshop observado; o mesmo padrão em atividade regular produzirá falso “aberto”.

### MÉDIO — datas pareadas na mesma frase recebem a mesma função

**Arquivos/linhas:** `automacao/coletar.py:345-355, 416-430`.

**Entrada reproduzível:** “A abertura ocorre em 27/07 e o prazo fecha em 01/08.”

**Saída errada:** 27/07 e 01/08 como `inicio`; nenhum alerta de fechamento. A classificação deve usar a distância entre cada ocorrência de data e os gatilhos, não uma decisão única para o fragmento.

### MÉDIO — cache de prazos não tem versão de esquema

**Arquivos/linhas:** `automacao/coletar.py:611-625, 668-674, 679-683`; `docs/estado.json`.

**Entrada real:** 16 objetos persistidos sem `hora_certa`/`escopo`.

**Saída:** mistura de objetos antigos e novos no mesmo `data.json`. Não confirmei ação atual errada exclusivamente por essa mistura; portanto o impacto visível presente é **suspeita não confirmada**, embora a inconsistência seja factual.

### BAIXO — `cronograma.ics` não é uma quarta fonte independente

O HTML e o ICS são gerados do mesmo JSON público `cronograma_regular_3.json`. O arquivo contém os mesmos 8 inícios, 7 vencimentos e 7 carências: 22 `VEVENT`, sem datas adicionais.

Além disso, o gerador usa UID aleatório a cada download e horários “flutuantes” como `T235900`, sem `TZID` ou `Z`. Reimportações podem duplicar eventos e calendários em outro fuso podem interpretar 23:59 localmente. Vale como redundância de formato, não como fonte independente de verdade.

## 5. Inventário AVA × robô atualizado

| Superfície | O que observei no AVA | Estado do robô | Lacuna relevante |
|---|---|---|---|
| Meus cursos | Quatro disciplinas atuais | Captura 4/4 | Contrato aceita 3/4 ou 2/4 |
| Cronograma regular 3º bimestre | Semanas 1–7 com início, vencimento e carência; revisão | Captura HTML corretamente | ICS não acrescenta cobertura |
| Calendário Moodle | Três fechamentos de quiz S1 em 02/08 23:59 | Captura 3/3 por `cmid` | API e DOM ainda não são unidos/paginados |
| Notificações | Três não lidas: quizzes S2 abrem em 27/07 | Captura assunto/link e mostra em “novidades” | Não antecipa item/ação; aceitável como abertura, mas útil para planejamento |
| Fóruns oficiais | Um post atual com prazos materiais: M4 26/07, entrega 01/08, pares 04/08 | Os três fechamentos estão na fila | Limite efetivo de cinco únicos em fóruns de discussão única |
| Fóruns massivos | Pelo menos 1.839 posts únicos nas discussões únicas inspecionadas, fora tópicos separados de grupo | Publica 11/11/11/15 avisos por curso | O volume bruto não é problema por si; o corte antes do dedup é |
| Quiz regular | “Aberto 20/07”, “Fecha 02/08 23:59”, 3 tentativas, maior nota, autoenvio no vencimento | Usa somente status do card, calendário e booleano aberto | Descarta janela, tentativas e estado de tentativa |
| SCORM COM170 | 0 tentativas, ilimitadas, maior tentativa, nota “Nenhum” | Captura Pendente/aberto | Não captura tentativas/nota nem distingue “nunca iniciado” |
| Tarefa AIA S2 | Vencimento, grupo, tentativa 1/3, enviado, data do envio, arquivo, feedback | AIA não entra no retrato útil | Para tarefas regulares, esses campos permitiriam estado bem mais confiável sem publicar nota |
| Workshop AIA S4 | Fases, janelas de envio/avaliação, envio ausente, avaliação não atribuída, prazo terminado | Não captura; `item_aberto` erraria sem atalho AIA | Precisa parser por tipo de atividade |
| Boletim COM170 | “Média AVA — Erro”; feedback S2 visível; SCORM sem nota | Não lê boletim | Monitorar presença de erro, feedback novo e “nota disponível” sem copiar valor |
| Boletins regulares | Um item de quiz S1, ainda sem nota | Não lê | Sem urgência hoje, mas feedback futuro seguirá invisível |
| Prova presencial | Calendário público atualizado em 25/07 lista provas antigas/2º bimestre; não contém COM100, SOC100, LET110 ou COM170 atuais | Invisível | A página afirma que, em divergência, vale o Sistema de Prova (`acesso.univesp.br`) |
| Sistema de Prova | Exige autenticação própria; a sessão do AVA não autenticou esse portal | Não captura | Data/horário confiáveis devem vir desse sistema. Polo/sala não foram verificáveis nesta sessão e não devem ser inventados |
| AIA encerrado | Tarefas e workshop realmente encerrados | Seção-pai vazia e ocultada | `encerrados=0` não mede cobertura de encerramento |

### Prova presencial: resposta objetiva

**Fato verificado:** a fonte pública contém data, faixa de horário, disciplina, curso/ano e período, mas ainda não lista as quatro disciplinas atuais. Cada card leva ao **Sistema de Prova**, e a própria página declara que o Sistema de Prova prevalece em caso de divergência.

**Não verificado:** polo e sala exatos de Josemar. O portal pediu nova autenticação; a sessão já logada do AVA não bastou.

**Captura confiável proposta:** coletor separado e autenticado para o Sistema de Prova; registrar disciplina/código, data, início/fim, modalidade, polo, sala e timestamp da consulta; reconciliar com o calendário público e falhar fechado em divergência ou campo obrigatório ausente. Não inferir sala pelo cadastro do polo.

### Fóruns: conta de prazos

Na leitura desta rodada, o único post oficial corrente com fechamentos materiais é o aviso da Q1 da COM170, e os três fechamentos foram capturados. Os demais posts explícitos com datas encontrados em discussões únicas eram principalmente conversa de aluno, data de live sem autoridade confirmada, link bibliográfico com ano, abertura de semana ou prazo administrativo de aproveitamento; não deveriam virar automaticamente obrigação acadêmica.

Portanto, **não encontrei prazo oficial atual perdido no retrato de 25/07**. O problema confirmado é estrutural: o cache retém só cinco posts únicos por discussão e não sinaliza truncamento.

## 6. Testes faltantes

Casos concretos prioritários:

1. **Cobertura 4→3 e 4→2**

   ```python
   ok, _ = validar_cobertura(nova_com_3_cursos, anterior_com_4)
   assert not ok
   ```

   Acrescentar caso de transição oficial de bimestre com sinal explícito, para não fixar “sempre quatro”.

2. **Dois deveres legítimos com mesmo verbo/hora**

   ```python
   p1 = prazo("Fechamento da submissão individual", "2026-08-01T23:59:00-03:00")
   p2 = prazo("Fechamento da submissão do grupo", "2026-08-01T23:59:00-03:00")
   assert nomes(montar_acoes(...)) == {p1.rotulo, p2.rotulo}
   ```

3. **Reset de escopo**

   ```python
   texto = "Módulo 4: entregue até 26/07.\nLIVE MAGNA: será realizada em 30/07."
   assert casar_prazos("Módulo 4", extrair_prazos(texto, ref)) == [prazo_26]
   ```

4. **Abertura e fechamento na mesma frase**

   ```python
   p = extrair_prazos("A abertura ocorre em 27/07 e o prazo fecha em 01/08.", ref)
   assert tipos(p) == {"27/07": "inicio", "01/08": "fim"}
   ```

   Incluir também “abre em 27/07 e fecha em 01/08”, que hoje retorna vazio.

5. **DOM realista de fórum e corte**

   Fixture com `article.forum-post-container` contendo filho `[data-region=post]`, seis posts únicos relevantes e duplicação estrutural. Verificar que `JS_POSTS` devolve seis, o cache guarda seis e nenhum corte ocorre antes do dedup.

6. **Migração do cache**

   Carregar post cacheado sem `hora_certa`/`escopo` após incrementar `EXTRATOR_SCHEMA`; esperar reprocessamento e objeto completo.

7. **Item inacessível não é aberto**

   ```python
   assert item_aberto(page_com_login, url) is None
   assert item_aberto(page_sem_permissao, url) is None
   assert item_aberto(page_com_texto("Submissões fechadas"), url) is False
   assert item_aberto(page_com_texto("O prazo de envio terminou"), url) is False
   ```

8. **Predecessores com prefixo alterado**

   Verificar `Atividade M3 - ...`, `Quiz M3 - ...`, rótulo duplicado e ciclo. O teste deve exigir falha explícita/diagnóstico, não prioridade silenciosamente ausente.

9. **Repost antigo**

   ```python
   p = extrair_prazos("Relembrando: o prazo foi até 26/07.", ref_2027_04_20)
   assert p == []  # ou exigir ano/linguagem futura; nunca promover silenciosamente
   ```

10. **Fluxo da Action em coleta incompleta**

    Teste de integração: coletor retorna 2; confirmar que o retrato anterior não é substituído, que o alerta desejado é renderizado/publicado por um caminho controlado e que nenhum e-mail usa assunto de sucesso.

11. **Fixture integral do aviso real**

    Usar o texto completo de 24/07, incluindo AIA 20/07, Módulo 5 “a confirmar”, Módulos 6 e 7 e LIVE INICIAL. A fixture atual em `testes/test_prazos.py:63-70` é uma versão limpa que remove justamente as transições de assunto perigosas.

12. **Teste de login menos permissivo**

    Manter o servidor local, mas usar porta efêmera, `try/finally` para encerramento e uma fixture do HTML atual. O teste `test_login.py:189-190` apenas procura a palavra `print` no corpo de uma função; isso não demonstra ausência de vazamento por exceção, URL ou chamada indireta.

## 7. O que verifiquei e está correto

- Li o relatório da rodada 1, `STATUS.md`, código atual, workflow, renderização e estado persistido.
- As 49 verificações de `test_prazos.py` e as 12 de `test_login.py` passaram.
- O workflow realmente executa os testes antes de restaurar sessão e acessar o AVA.
- Quatro disciplinas, 36 seções, 56 itens, 48 avisos, 3 eventos e 35 ações batem com o retrato atual.
- O site mostra corretamente duas ações apertadas: quiz M1 como prioridade sem prazo próprio e Módulo 4 com vencimento oficial em 26/07 23:59.
- O texto “faça antes de” preserva a distinção entre prioridade derivada e prazo oficial.
- O aviso repetido não duplica a obrigação atual.
- Entrega e avaliação por pares aparecem como duas fases, com verbos corretos.
- Hora explícita do M4 é preservada; datas sem hora não são apresentadas como 23:59.
- Os três quizzes S1 fecham em 02/08 23:59 no AVA e no retrato.
- O cronograma HTML foi interpretado corretamente; o JSON/ICS confirma as mesmas datas.
- Nenhum prazo oficial corrente encontrado nos fóruns ficou demonstravelmente ausente na coleta de 25/07.
- O boletim COM170 continua com erro de cálculo, e o feedback S2 continua acessível; não observei publicação desse feedback ou de nota no site público.
- Não encontrei novo vetor de mensagem privada ou nota publicado. O risco aceito de posts públicos de colegas não foi reaberto.

## Síntese de prioridade

1. Desduplicar posts **antes** de aplicar qualquer teto e publicar métricas de truncamento.
2. Fazer o contrato de saúde detectar perda de qualquer curso ativo, com tratamento explícito de transição de bimestre.
3. Trocar a identidade da obrigação por chave semântica estável, não `(quando, verbo)`.
4. Classificar cada data por sua vizinhança e encerrar/resetar escopo ao mudar de bloco.
5. Separar “Action falhou” de “como alertar no site/e-mail” sem publicar uma coleta ruim.

