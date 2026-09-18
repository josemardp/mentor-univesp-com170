# Auditoria independente — rodada 3

**Data:** 25/07/2026  
**Commit auditado:** `26b00a4`  
**Escopo:** heurísticas introduzidas na rodada 2, utilidade do e-mail/site e proposta contida de modularização.

# 1. Frente A — ataque às dez heurísticas

Legenda:

- **Quebrei:** há entrada executável com saída errada.
- **Quebra na condição X:** o caso atual funciona, mas a regra falha sob uma
  condição delimitada.
- **Não quebrei:** os ataques pedidos e os dados atuais se comportaram
  corretamente.

| # | Heurística | Veredito | Evidência observada |
|---|---|---|---|
| 1 | `encerra_escopo()` | **Quebrei** | `Módulo 4: entrega até 26/07. LIVE MAGNA será realizada em 30/07.` mantém o escopo do Módulo 4 e `casar_prazos("Módulo 4", ...)` recebe também 30/07. Sem `:`, a mudança de assunto não é percebida. No sentido oposto, `Módulo 4: orientações. Grupo A: entrega até 26/07.` zera o escopo e o prazo não encontra o Módulo 4. |
| 2 | `_tipo_prazo()` por posição | **Quebrei** | `27/07 (abertura das inscrições), 01/08 (fechamento das inscrições)` classifica **as duas** datas como `inicio`; o fechamento some. `Abertura das submissões: de 27/07 a 01/08` também classifica as duas como abertura. `Não haverá entrega em 30/07` produz `fim` em 30/07, inventando uma obrigação que a frase nega. O caso simples `27/07, abertura...` funciona. |
| 3 | `casar_prazos()` só pelo rótulo | **Quebra na condição de escopo não detectado** | No aviso real de 24/07, os prazos com dono continuam corretos: M4→26/07, M6→01/08 e M6→04/08; abertura e live não viram prazo de módulo. Mas, se o escopo for perdido por `Grupo A:` ou por uma fase fora de `PALAVRAS_FASE`, o rótulo não contém “Módulo 4” e o prazo real fica sem dono. |
| 4 | `validar_cobertura()` por ID | **Quebrei** | Anterior `A(id=1), B(id=2)` → atual `B(id=2), C(id=3)` retorna `(True, [])`: a entrada de qualquer ID mascara a perda de outro. Anterior sem IDs `A,B` → atual apenas `A` também retorna saudável, pois `ids_antes` fica vazio. Uma disciplina que termina legitimamente sem entrar outra gera falso alarme; um mesmo curso cujo ID muda é aceito como troca. |
| 5 | Dedup de fase por `(quando, rotulo[:60])` | **Quebrei nos dois sentidos** | Mesmo horário com `Fechamento das submissões` e `Fechamento das submissões do trabalho` gera duas ações equivalentes. Dois rótulos distintos com o mesmo prefixo de 60 caracteres — `Entrega da atividade final para composição da avaliação do módulo ... individual` / `... em grupo` — viram uma única ação. |
| 6 | Dedup de posts por `(data, texto[:80])` | **Quebra na condição X** | Dois posts de autores diferentes, no mesmo segundo, ambos com `Bora!`, viram um só. Mesmo minuto com segundos diferentes não colide; mesmo autor/segundo com texto diferente também não. Nos 284 posts reais medidos hoje (31 + 41 + 212), não houve colisão. Post editado não duplica dentro da leitura atual, mas pode ficar velho no cache se a edição não alterar o marcador `ultimo`. Essa última parte é **suspeita não confirmada**. |
| 7 | `JS_POSTS`, primeiro seletor que casar | **Não quebrei no DOM real** | `article`, `[data-region="post"]` e `.forumpost` retornaram respectivamente 31/31/31 no Q1 geral, 41/41/41 no fórum geral, 212/212/212 no fórum regular e 1/1/1 na discussão do aviso. A página-lista de Avisos retornou 0/0/0 e oito links de discussão, corretamente tratada por `JS_DISCUSSOES`. O primeiro seletor é um envelope, mas há correspondência um-para-um com posts nesses quatro formatos. |
| 8 | `SINAIS_INDEFINIDO` → `None` | **Quebrei no consumidor** | Um item `Pendente`, `conta_nota=True`, `aberto=None` entra normalmente em `acoes`, com `urgencia="sem_prazo"`, sem qualquer marca de incerteza. `None` não deve esconder o item, pois isso criaria omissão; deve mantê-lo e exibir **“não consegui verificar se está aberto”**. |
| 9 | `gerar_guia` retorna 0 em coleta incompleta | **Não quebrei o fluxo atual** | Simulação `coletar.main() → 2`, `render.main() → 0` resultou em código 0; o assunto foi `[Univesp 25/07] leitura incompleta, confira no AVA`. O workflow envia o e-mail, commita/publica o último retrato válido com aviso e só então falha em “Verificar saúde”. Exceção não controlada em coleta ou render continuou propagando `RuntimeError` e derrubando o job. |
| 10 | `achar_datas()` pelo ano mais próximo | **Não quebrei nos casos pedidos** | Referência 15/12/2026 + `28/12 a 03/01` produziu 28/12/2026→03/01/2027. Datas explícitas `20/12/2026 a 10/01/2027` foram preservadas. Referência 20/12/2026 + próximo bimestre `15/01 a 20/03` produziu 2027. Cronograma com datas sem ano que cubra mais de cerca de um ano continua inerentemente ambíguo, mas não é o formato observado. |

## Os sete achados da rodada 2 continuam corrigidos?

| Achado da rodada 2 | Situação nesta rodada |
|---|---|
| Escopo vazava para live e prova com novo rótulo | **Corrigido no caso original.** O teste `LIVE MAGNA:` / `Prova presencial:` passou, e o aviso real de 24/07 não atribuiu a live ao Módulo 4. Há novo caso vizinho sem dois-pontos, descrito acima. |
| Duas datas na mesma frase viravam abertura | **Corrigido no caso original.** `A abertura ocorre em 27/07 e o prazo fecha em 01/08` resultou `inicio` e `fim`. Há novo caso vizinho com gatilho depois da segunda data. |
| Perder até metade das disciplinas passava | **Corrigido no caso original.** Quedas 4→3, 4→2 e 4→1, sem IDs novos, foram recusadas. Há mascaramento quando entra qualquer ID novo. |
| Dedup por verbo colapsava duas obrigações | **Corrigido no caso original.** Submissão individual e submissão do grupo, mesmo horário, geraram duas ações. O corte em 60 caracteres cria novas colisões. |
| Seletores duplicavam posts antes do corte | **Corrigido.** O código usa um seletor, deduplica antes de limitar e registra truncamento. O DOM real confirmou a cardinalidade dos seletores. |
| Item fechado era tratado como aberto | **Corrigido no caso original.** `Submissões fechadas` e `o prazo de envio terminou` estão nos sinais de fechamento e retornam falso. A incerteza (`None`) ainda é apresentada como aberta pelo consumidor. |
| Coleta incompleta não chegava ao site/e-mail | **Corrigido.** Render, assunto, publicação do aviso e falha final do workflow estão na ordem planejada. |

### A suíte ficou frouxa?

**Não houve afrouxamento observável.** O diff adaptou a aridade de
`achar_datas()`, adicionou IDs às fixtures e acrescentou casos; não trocou
expectativas fortes por expectativas permissivas, não adicionou `skip` e não
removeu um caso de falha.

Há, porém, uma diferença entre “não ficou frouxa” e “protege os sete
consertos”. Três pontos ainda não têm teste comportamental suficiente:

1. não há fixture DOM para `JS_POSTS`, dedup antes do corte e flag
   `truncado`;
2. os testes de `item_aberto()` apenas verificam se frases existem nas listas
   de sinais; não chamam a função nem verificam como `None` chega à ação;
3. não há teste automatizado da sequência
   coleta incompleta→render→assunto→publicação→falha de saúde.

Portanto: os 73 checks estão verdes e não foram relaxados, mas ainda não
congelam integralmente os sete comportamentos de produção.

---

# 2. Achados novos por severidade

## Crítico — mudança de assunto sem `:` volta a inventar prazo

**Arquivo/linha:** `automacao/coletar.py:421-438`,
`automacao/coletar.py:475-479`, `automacao/coletar.py:1062-1068`.

**Fato reproduzido**

Entrada:

```text
Módulo 4: entrega até 26/07.
LIVE MAGNA será realizada em 30/07.
```

Saída errada:

```text
casar_prazos("Módulo 4") → 26/07 e 30/07
```

30/07 é a data da live, mas vira prazo do Módulo 4 porque a segunda frase não
tem dois-pontos e não encerra o escopo anterior.

**Condição:** a correção funciona quando o novo assunto é `LIVE MAGNA: ...`;
quebra quando a mesma mudança é escrita como frase.

**Direção de correção sugerida:** o escopo não pode depender apenas de
pontuação. Cada prazo deveria carregar evidência explícita de dono; na dúvida,
ficar órfão e visível para diagnóstico, nunca herdar o último módulo.

## Crítico — negação é aceita como prazo afirmativo

**Arquivo/linha:** `automacao/coletar.py:341-357`,
`automacao/coletar.py:360-392`, `automacao/coletar.py:482-496`.

**Fato reproduzido**

Entrada:

```text
Não haverá entrega em 30/07.
```

Saída errada:

```json
{"quando":"2026-07-30T23:59:00-03:00","tipo":"fim"}
```

O pré-filtro encontra `entrega`; `_tipo_prazo()` encontra gatilho de fim e não
considera a negação.

**Direção de correção sugerida:** detectar negação na oração que governa a
data e recusar o candidato; não tentar converter negação em outra semântica.

## Alto — fechamento depois da data é classificado como abertura

**Arquivo/linha:** `automacao/coletar.py:360-381`.

**Fato reproduzido**

Entrada:

```text
27/07 (abertura das inscrições), 01/08 (fechamento das inscrições).
```

Saída errada:

```text
27/07 → inicio
01/08 → inicio
```

Para 01/08, existe `abertura` antes e `fechamento` depois. A regra prefere
qualquer gatilho anterior, ainda que o posterior seja o que governa a data.
Resultado: o fechamento que valeria alerta some.

Intervalos também são ambíguos:

```text
Abertura das submissões: de 27/07 a 01/08.
```

produz duas aberturas. A segunda data deveria ser o fim do intervalo, mas isso
não pode ser inferido com segurança só pela lista de palavras.

## Alto — subtítulo ou fase fora da lista apaga o dono do prazo

**Arquivo/linha:** `automacao/coletar.py:416-438`,
`automacao/coletar.py:475-479`, `automacao/coletar.py:1049-1068`.

**Fato reproduzido**

Entrada:

```text
Módulo 4: orientações.
Grupo A: entrega até 26/07.
```

Extração:

```text
rotulo = "Grupo A"
escopo = None
casar_prazos("Módulo 4") = []
```

O mesmo ocorre com:

```text
Módulo 4: orientações.
Divulgação do resultado: data 30/07.
```

`Grupo A` é subtítulo; `Divulgação do resultado` pode ser fase. Ambos são
tratados como assunto novo porque não estão em `PALAVRAS_FASE`.

**Hipótese delimitada:** não encontrei esses dois rótulos no aviso atual de
24/07. O comportamento do parser, porém, foi reproduzido.

## Alto — qualquer disciplina nova mascara a perda de uma conhecida

**Arquivo/linha:** `automacao/coletar.py:1296-1309`.

**Fato reproduzido**

Entrada anterior:

```text
A(id=1), B(id=2)
```

Entrada atual:

```text
B(id=2), C(id=3)
```

Saída errada:

```text
(True, [])
```

A condição `sumiram and not novas` presume que qualquer ID novo transforma
qualquer perda em troca legítima. Uma nova disciplina realmente adicionada no
mesmo dia em que a raspagem perde outra mascara a falha.

Também confirmei:

- histórico sem IDs → a comparação desliga e uma queda 2→1 passa;
- A(id=1) → A(id=9) passa como troca;
- A,B → apenas B é recusado, mesmo que A tenha terminado legitimamente.

O último é falha segura, não omissão: mantém retrato anterior e avisa. A regra
precisa distinguir **mudança de matrícula** de **perda de leitura**, não
deduzir a diferença só pela existência de IDs novos.

## Alto — corte de 60 caracteres omite obrigações distintas

**Arquivo/linha:** `automacao/coletar.py:1124-1133`.

**Fato reproduzido**

Entradas no mesmo horário:

```text
Entrega da atividade final para composição da avaliação do módulo individual
Entrega da atividade final para composição da avaliação do módulo em grupo
```

Os primeiros 60 caracteres normalizados coincidem. Saída: uma ação em vez de
duas.

No sentido contrário:

```text
Fechamento das submissões
Fechamento das submissões do trabalho
```

produz duas ações, embora possa ser a mesma obrigação repetida com pequena
variação.

**Direção de correção sugerida:** usar identidade semântica estruturada
(`curso`, `módulo`, `fase`, `quando`, fonte/ID do post) e manter duplicatas
duvidosas agrupadas, em vez de decidir por prefixo textual.

## Médio — “não consegui verificar” é exibido como pendência normal

**Arquivo/linha:** `automacao/coletar.py:814-828`,
`automacao/coletar.py:1029-1033`, `automacao/coletar.py:1148-1176`.

**Fato reproduzido**

Entrada:

```json
{
  "status": "Pendente",
  "conta_nota": true,
  "aberto": null,
  "label": "Quiz",
  "type": "quiz"
}
```

Saída:

```text
ação normal, urgência "sem_prazo", sem marca de falha de verificação
```

Comportamento recomendado: **manter a ação** para não omitir, mas adicionar
`verificacao="indefinida"` e uma indicação explícita no site/e-mail. Se a
indefinição vier de login/permissão, também deve degradar a saúde da fonte.

## Baixo — dedup de posts pode colidir entre autores

**Arquivo/linha:** `automacao/coletar.py:705-719`.

**Fato reproduzido**

Entrada:

```json
[
  {"autor":"Ana","data":"2026-07-25T10:00:00-03:00","texto":"Bora!"},
  {"autor":"Bia","data":"2026-07-25T10:00:00-03:00","texto":"Bora!"}
]
```

Saída: só o primeiro post.

Não houve colisão nos 284 posts reais medidos. Por isso a severidade é baixa e
a condição é estreita. O ID Moodle do post já existe no DOM (`p450361`,
`data-post-id=450361`) e é uma chave mais forte.

## Suspeitas não confirmadas

- **Edição de post sem alterar `ultimo`:** o cache pode não reler a discussão e
  manter texto antigo. Não editei nem encontrei histórico de edição que
  permitisse provar isso.
- **Tema escuro:** o CSS define paleta escura, mas não há controle de tema na
  página e o perfil usado estava em modo claro. A política do navegador impediu
  injeção de JavaScript para forçar o atributo. Fiz inspeção visual real em
  desktop/celular claro e inspeção estática da paleta escura; não considero o
  modo escuro visualmente verificado.

---

# 3. Frente B — crítica do produto

## B.1 E-mail das 8h

### Em 10 segundos ele sabe o que fazer?

**Parcialmente.** Ele percebe que há duas coisas apertadas, mas a primeira
parece vencer amanhã e não mostra prazo. Só quem já conhece o modelo entende
que o quiz não vence: ele foi promovido porque destrava o Módulo 4.

O assunto `2 coisas vencendo` é factualmente impreciso: há **um prazo próprio**
e **uma dependência prioritária**.

### O que é ruído

- a lista de 19 itens sem prazo mistura obrigação avaliativa com higiene de
  conclusão do Moodle;
- seis posts de colegas não mudam a decisão de estudo;
- três notificações idênticas de abertura deveriam ser uma linha;
- referências bibliográficas inteiras dificultam varrer a tela;
- repetir item por item de uma mesma semana esconde a unidade de trabalho:
  “LET110 — concluir pacote da Semana 1”.

Os títulos completos têm valor dentro do mapa/site, quando Josemar já decidiu
qual disciplina abrir. No e-mail, atrapalham.

### O que falta

- distinguir visual e verbalmente **prazo próprio** de **faça antes porque
  destrava**;
- uma ação inicial inequívoca;
- agrupar atividades da mesma disciplina/data;
- dizer que o Módulo 4 ainda está bloqueado e que há uma cadeia M1→M2→M3→M4;
- separar “vale nota, sem prazo confirmado” de “marque como concluído”.

### Assunto recomendado

```text
[Univesp 25/07] Hoje: destravar COM170; entrega amanhã 23:59
```

Ele informa a decisão e o prazo real sem atribuir o vencimento ao quiz.

### E-mail reescrito por inteiro, com os mesmos dados

```text
ASSUNTO: [Univesp 25/07] Hoje: destravar COM170; entrega amanhã 23:59

Guia Univesp — sábado, 25/07/2026

FAÇA AGORA
- COM170: conclua “M1 — Quiz: Identifique o paradigma”.
  Ele NÃO tem prazo próprio; está no topo porque destrava M2 → M3 → M4.

PRAZO DURO
- Amanhã, 26/07 às 23:59: entregue o trabalho do Módulo 4.
  Ele ainda está bloqueado; avance pelos módulos anteriores para abri-lo.

DEPOIS
- 29/07 às 23:59: conclua o pacote da Semana 1 de LET110
  (videoaula + 4 textos) e de SOC100 (2 textos + 2 vídeos).
- 01/08 às 23:59: entregue o trabalho em grupo de COM170.
- 02/08: responda as Atividades Avaliativas S1 de COM100, LET110 e SOC100.
- 04/08: faça a avaliação por pares de COM170.

VALE NOTA, MAS NÃO ACHEI PRAZO
- COM170: gravação da Live com facilitador.

ABERTURAS E NOVIDADES
- Em 27/07 abrem as três Atividades Avaliativas da Semana 2.
- Posts de fórum e a lista completa de itens ficam no site; nenhum dos posts
  novos de hoje muda a prioridade acima.

Detalhes, fontes e links:
https://esdraaline.github.io/mentor-univesp-com170/
```

## B.2 Site

### O que observei

**Desktop claro**

- tipografia legível e coluna estreita confortável;
- sem problema de alinhamento;
- muito espaço lateral, mas isso não prejudica a leitura;
- a decisão urgente vem depois de um recado longo.

**Celular claro**

- sem estouro horizontal (`scrollWidth=clientWidth`);
- fonte e cartões permanecem legíveis;
- a primeira tela inteira mostra cabeçalho e recado; “O que fazer agora” não
  aparece na dobra inicial.

**Escuro**

- inspeção visual não concluída, pelos motivos registrados em “suspeitas não
  confirmadas”;
- inspeção estática confirmou variáveis próprias para fundo, papel, texto,
  estados e sombras em `automacao/render.py:454-466`.

### O que ele consegue decidir hoje

Depois de rolar o recado, ele consegue decidir que o quiz M1 é a primeira ação
e entende por que ele subiu. Também vê o prazo e a fonte do Módulo 4.

O que ainda exige abrir o AVA:

- saber quanto falta dentro de M2/M3/M4;
- executar a atividade;
- confirmar estado real quando `item_aberto()` devolveu `None`;
- ler conteúdo e instruções completas;
- distinguir quais “A marcar” são apenas higiene de conclusão.

### Nova ordem proposta

1. **Saúde e atualização**, em uma faixa compacta: última leitura, fontes com
   falha e se os dados são atuais.
2. **Agora — uma única próxima ação**, com botão direto: quiz M1; “sem prazo
   próprio; destrava M4”.
3. **Prazo duro relacionado:** M4, 26/07 23:59, ainda bloqueado; mostrar a
   cadeia M1→M2→M3→M4.
4. **Próximos sete dias**, agrupados por entrega/disciplina, não por cada
   recurso bibliográfico.
5. **Vale nota sem prazo confirmado**, separado de pendências administrativas.
6. **Mudanças que pedem atenção:** avisos oficiais e notificações consolidadas.
   Posts comuns de colegas ficam recolhidos como “Fóruns — N novos”.
7. **Mapa das disciplinas**, todo recolhido por padrão; abre quando Josemar já
   escolheu a matéria.
8. **Higiene do AVA**, recolhida: páginas “Início”, “Em síntese”,
   “Referências” e marcações manuais.
9. **Já encerrou**, recolhido no rodapé ou fora da tela principal.
10. **Recado da mentora**, abaixo das decisões e recolhido. Só sobe quando
    contém correção/alerta que a coleta automática não consegue expressar e
    traz data de validade.

### O que eu cortaria por inteiro da superfície principal

- corpo de posts comuns de colegas, por falta de utilidade decisória nesta
  tela — esta é uma decisão de produto, não uma reabertura da decisão de
  privacidade;
- lista expandida de 19 itens sem prazo;
- títulos bibliográficos integrais no bloco “Agora”;
- repetição de notificações idênticas;
- recado semanal na primeira posição.

O recado atual agrega uma correção importante e explica a cadeia do COM170.
Mas compete com a lista porque repete os mesmos fatos em prosa e envelhece
entre revisões. Deve ser anotação excepcional, datada e secundária.

## B.3 Uma tela e um e-mail de cinco linhas

### O que sobreviveria na única tela

1. **Dados confiáveis?** Última leitura e saúde das fontes.
2. **Faça isto agora:** uma ação com link.
3. **Por quê:** prazo duro, dependência e bloqueio.
4. **Próximos sete dias:** entregas agrupadas por data.
5. **Sem prazo confirmado, mas vale nota:** bloco curto.
6. Um link/expansor para mapa, fóruns e higiene.

Isso sobrevive porque responde às três perguntas do uso real: “posso confiar?”,
“o que faço nesta janela?” e “o que vem logo depois?”.

### E-mail de cinco linhas

```text
1. HOJE: faça o quiz M1 de COM170 — sem prazo próprio; ele destrava M2→M4.
2. PRAZO: Módulo 4 amanhã, 26/07 às 23:59; ainda está bloqueado.
3. 29/07: pacotes S1 de LET110 e SOC100; 01/08: grupo COM170.
4. 02/08: quizzes S1 de COM100/LET110/SOC100; 04/08: pares COM170.
5. Dados lidos 25/07 18:47 — fontes e links: [abrir guia].
```

---

# 4. Frente C — divisão modular contida

## Princípio

Separar por **responsabilidade e fronteira de falha**, não apenas por tamanho.
Cada fonte devolve dados, saúde e idade próprias. Uma falha de fórum não deve
derrubar a leitura das disciplinas; também não deve transformar silêncio em
“tudo em dia”.

## Estrutura proposta

```text
automacao/
  modelos.py
  configuracao.py
  persistencia.py
  saude.py

  dominio/
    datas.py
    prazos.py
    acoes.py
    dependencias.py

  fontes/
    moodle.py
    disciplinas.py
    calendario.py
    cronograma.py
    foruns.py
    itens.py
    notificacoes.py

  pipeline.py
  coletar.py
  render.py
  enviar_email.py
```

### Contratos

`modelos.py`

- `SourceResult[T]`: `status`, `dados`, `problemas`, `checked_at`,
  `from_cache`, `truncado`;
- modelos mínimos para `Curso`, `Secao`, `Item`, `Prazo`, `Acao`;
- sem lógica de rede ou render.

`configuracao.py`

- URLs, limites, janelas, caminhos e fuso;
- nenhuma leitura do AVA.

`persistencia.py`

- carregar/gravar `data.json` e estado por fonte;
- escrita atômica;
- versão do esquema de cache.

`saude.py`

- validação de cobertura;
- política “publicar atual / preservar último válido / falhar”;
- saúde agregada e saúde por fonte.

`dominio/datas.py`

- `achar_datas()`, meses e normalização temporal;
- funções puras, sem `datetime.now()` interno: referência sempre recebida.

`dominio/prazos.py`

- extração, negação, escopo, classificação início/fim e casamento;
- devolve candidatos órfãos em vez de descartá-los silenciosamente.

`dominio/acoes.py`

- `montar_acoes()`, verbos, urgência e dedup semântico;
- recebe cursos/prazos prontos.

`dominio/dependencias.py`

- predecessor, cadeia e propagação de prioridade;
- nunca altera prazo próprio.

`fontes/moodle.py`

- cliente comum de página/API, sessão e erros normalizados;
- não conhece regra de negócio de prazo.

`fontes/disciplinas.py`

- descoberta e estrutura de cursos/seções;
- expõe `coletar_disciplinas(ctx) -> SourceResult[list[Curso]]`.

`fontes/calendario.py`

- API + fallback DOM;
- paginação e dedup por ID de evento ficam isolados aqui.

`fontes/cronograma.py`

- leitura de linhas e conversão para semanas;
- usa `dominio.datas`.

`fontes/foruns.py`

- lista/discussão, seletores, parsing de posts, cache e truncamento;
- expõe também métricas de seletor e colisão para teste/diagnóstico.

`fontes/itens.py`

- estado aberto/fechado/indefinido;
- `Indefinido` é estado explícito, não `None` interpretado implicitamente.

`fontes/notificacoes.py`

- notificações e mensagens, consolidação por assunto/atividade.

`pipeline.py`

- executa fontes independentemente;
- combina resultados;
- preserva por fonte o último dado válido;
- aplica política de saúde e chama montagem de ações.

`coletar.py`

- fica como ponto de entrada compatível, com aproximadamente 50–100 linhas;
- cria contexto, chama `pipeline.executar()`, persiste e devolve o código.

## Como uma parte falha sem derrubar o resto

Exemplo de contrato:

```python
SourceResult(
    status="erro",
    dados=ultimo_forum_valido,
    problemas=["timeout no fórum COM170"],
    checked_at=agora,
    from_cache=True,
    truncado=False,
)
```

Regras propostas:

- descoberta de disciplinas/seções é **fonte estrutural obrigatória**; falha
  preserva o retrato inteiro e marca coleta incompleta;
- calendário, cronograma e fóruns são **fontes de prazo independentes**; se uma
  falhar, preserva-se somente o último resultado daquela fonte, com idade
  visível;
- uma fonte de prazo sem dado atual não autoriza remover prazo anterior;
- notificações/mensagens podem falhar sem bloquear ações, mas a falha aparece
  na saúde;
- erro inesperado de código continua derrubando o job; independência não deve
  engolir exceção de programação como se fosse ausência normal.

## Ordem de migração mantendo testes verdes

1. **Congelar comportamento atual.** Adicionar testes de caracterização para o
   aviso real de 24/07, os quatro formatos de fórum e o fluxo de coleta
   incompleta. Nenhuma mudança funcional.
2. **Extrair funções puras.** Mover normalização/datas para
   `dominio/datas.py`, mantendo reexports em `coletar.py`. Rodar 61+12.
3. **Extrair prazos e dependências.** Mover escopo, classificação, casamento e
   ações. Continuar com as mesmas assinaturas/reexports. Rodar 61+12 a cada
   arquivo.
4. **Extrair fórum e cache.** Primeiro parser DOM puro com fixtures; depois I/O
   de navegação. Adicionar teste de cardinalidade, dedup e truncamento.
5. **Introduzir `SourceResult` nas bordas.** Adaptar uma fonte por vez,
   começando por notificações e fóruns, que têm menor acoplamento estrutural.
6. **Separar calendário, cronograma e itens.** Cada migração mantém o JSON de
   saída comparado a um golden sanitizado.
7. **Extrair descoberta por último.** É a raiz dos IDs e seções; mover só
   depois de as fontes consumidoras já terem contratos.
8. **Trocar `coletar.py` pelo orquestrador fino.** Remover reexports apenas
   depois de repontar testes e confirmar duas execuções: saudável e fonte
   degradada.

Cada etapa deve ser um commit reversível. O critério não é só “testes verdes”:
o `docs/data.json` de uma fixture deve manter identidade de ações, prazos,
fontes e estados de saúde.

---

# 5. Perguntas objetivas para o Josemar

1. Quando você abre o e-mail com só 40 minutos disponíveis, prefere **uma ação
   recomendada** ou quer ver também todos os prazos dos próximos sete dias?
2. Posso limitar o e-mail a “agora + próximos sete dias” e deixar mapa, fóruns
   e higiene apenas no site?
3. Itens “A marcar” que não valem nota devem sumir da fila principal e ficar
   em “Higiene do AVA” recolhido?
4. A live que vale nota, mas não tem prazo confirmado, deve continuar no
   e-mail diário ou só aparecer no site?
5. Você usa de fato o bloco “Chegou novo” para decidir estudo, ou só abre
   fóruns quando uma tarefa exige?
6. O recado da mentora deve aparecer apenas quando houver uma correção/alerta
   novo, em vez de ocupar o topo durante a semana inteira?
7. Quando uma disciplina some e outra entra, você prefere falhar fechado e
   mostrar alerta até confirmar a troca, mesmo com risco de um falso alarme na
   virada de bimestre?

---

# 6. O que verifiquei e está correto

- Repositório estava limpo no commit `26b00a4` antes desta auditoria.
- `python testes/test_prazos.py`: **61/61** checagens passaram.
- `python testes/test_login.py`: **12/12** checagens passaram.
- Testes rodam antes de qualquer acesso ao AVA no workflow.
- O fluxo de login de uma e duas etapas continua coberto sem expor senha.
- O aviso real de 24/07 mantém os donos corretos:
  - Módulo 4 → 26/07 23:59;
  - Módulo 6 → submissão 01/08 23:59;
  - Módulo 6 → pares 04/08 23:59;
  - aberturas e live não são casadas como prazo de módulo.
- A cadeia de prioridade mantém o quiz sem prazo próprio e explica que ele
  destrava o Módulo 4.
- O site mostra a fonte de cada prazo.
- Coleta incompleta preserva o último retrato válido, renderiza alerta, usa
  assunto correto, publica o aviso e termina a Action em falha.
- Erros inesperados de coleta/render não são convertidos em sucesso.
- O DOM real do AVA estava autenticado e os seletores tiveram cardinalidade
  consistente nos quatro formatos medidos.
- Não houve colisão da chave atual de posts nos 284 posts reais verificados.
- No site claro, desktop e celular não apresentaram estouro horizontal; a
  tipografia é legível.
- A virada de ano de `achar_datas()` funcionou para próximo bimestre,
  semana cruzando dezembro/janeiro e anos explícitos.
- Não reavaliei prova presencial, boletim, previsão de nota nem a decisão de
  privacidade, conforme o escopo desta rodada.
