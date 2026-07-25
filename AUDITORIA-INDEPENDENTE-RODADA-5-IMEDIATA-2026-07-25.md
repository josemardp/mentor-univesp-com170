# Auditoria independente — rodada 5, fase imediata

**Data:** 25/07/2026
**Commit auditado:** `dd79c2b`
**Correções atacadas:** commit `6be7087` e integração/publicação subsequente
**Escopo:** fontes vazias, SMTP, frescor, escrita interrompida, identidade,
publicação e reconciliação AVA × site.

## 1. Veredito

A fila automática está correta no caminho feliz: AVA e site concordaram que a
próxima ação era o Quiz 1 do Módulo 2, os três cronogramas regulares foram
contados corretamente e a última Action terminou verde. Porém a proteção contra
perda das fontes **não segura duas falhas consecutivas**: a primeira falha é
barrada, grava os zeros como nova referência e a segunda passa como `ok` com
zero prazo. O cache também faz fórum offline parecer fonte viva. Frescor, SMTP,
identidade e publicação melhoraram, mas as correções estão parciais. O sistema
ainda não está homologado para operar sem supervisão.

---

## 2. Resultado por correção da rodada 4

| Correção | Veredito | Evidência |
|---|---|---|
| Saúde exige fontes de prazo | **Não segura** | Primeira perda total falha fechado; a segunda perda idêntica retorna `ok` |
| Relê cinco vezes/dia e avisa após 3h | **Parcial** | A fila atualizou corretamente, mas o banner é calculado só ao gerar o HTML e nunca envelhece no navegador |
| Falha SMTP derruba o passo | **Parcial** | Exceção SMTP retorna 1; ausência de Secrets ainda retorna 0 |
| Publicar antes de enviar e-mail | **Parcial** | `git push` precede SMTP, mas o workflow não espera o deploy do Pages |
| Cronograma só em curso regular | **Segura no cenário atual** | Telemetria e Action mostram 3 cronogramas, não 4 |
| Escrita JSON atômica | **Segura para um arquivo isolado, com ressalvas** | Interrupção antes do `replace` preservou o original; HTML e o par data/estado não são transacionais |
| Identidade por `cmid` | **Segura quando o `cmid` existe e mantém o tipo** | Sem `cmid` ainda há colisão; `1` numérico → `"1"` textual vira item “novo” |

---

## 3. AVA × site

### Fila automática — passou

Estado observado ao vivo na COM170:

- Módulo 1: cinco itens concluídos.
- Módulo 2: os quatro primeiros itens concluídos.
- `173838` — Quiz 1: pendente.
- `173839` — Quiz 2: pendente.
- Módulo 3: bloqueado até concluir o Quiz 1.

Site, leitura de 25/07 às 19:33:

- primeira ação: `M2 - Quiz 1: Tipos de aprendizado de máquina`;
- segunda pendência sem prazo: Quiz 2;
- Módulo 4 continua bloqueado e com prazo do aviso em 26/07.

Portanto, a coleta e a propagação de prioridade acompanharam corretamente o
estado vivo.

### Recado editorial — falhou

O recado da mentora, exibido **antes** da fila correta, ainda afirma:

> você ainda está parado no quiz do Módulo 1

e termina com:

> Foco de hoje é só um: destravar o Módulo 1.

Isso contradiz o AVA e a própria fila automática logo abaixo. O recado foi
escrito às 15:20 e não possui validade, dependência de snapshot ou supressão
quando a atividade citada muda de estado.

**Arquivo/linhas:** `docs/revisao.json`,
`automacao/render.py:102-120`.

**Correção sugerida:** recado manual deve carregar `valid_until`,
`snapshot_id` ou IDs das atividades a que se refere. Se qualquer condição
deixar de valer, recolher o recado e mostrar “recado antigo”, sem orientação
imperativa.

---

## 4. Fontes vazias e silêncio

### Crítico 1 — falha fechado dura apenas uma execução

**Arquivos/linhas:** `automacao/coletar.py:1429-1442`,
`automacao/coletar.py:1527-1539`.

**Teste reproduzido**

Estado anterior:

```text
avisos=12, calendário=3, cronograma=1, itens_com_prazo=1
```

Primeira leitura com tudo zerado:

```text
validar_cobertura → False
main → rc=2, status=coleta_incompleta
```

Na saída de falha, o código preserva os cursos antigos, mas substitui
`fontes` pelos contadores atuais, todos zero. A segunda leitura idêntica usa
esses zeros como referência:

```text
validar_cobertura → True
main → rc=0, status=ok, zero fontes e zero prazo
```

Esta é exatamente a omissão silenciosa que a correção pretendia impedir.

**Correção sugerida:** separar `fontes_ultima_tentativa` de
`fontes_ultimo_snapshot_valido`. Uma falha nunca pode promover sua própria
telemetria a baseline. A validação seguinte deve continuar comparando contra o
último snapshot `ok`.

### Crítico 2 — fórum offline parece saudável quando há cache

**Arquivo/linhas:** `automacao/coletar.py:753-849`.

**Teste reproduzido**

- `page.goto()` do fórum lançou `TimeoutError`;
- o cache continha um aviso antigo;
- `varrer_foruns()` devolveu o aviso cacheado;
- `resumo_fontes()` contou `avisos=1`;
- `validar_cobertura()` retornou `(True, [])`.

O cache é necessário para manter prazos já descobertos, mas não é prova de que
a fonte foi lida hoje. Um novo aviso crítico pode ter sido publicado durante a
pane e será omitido.

**Correção sugerida:** cada fonte precisa de estado independente:

```text
status = live | cache | falhou | vazio_confirmado
last_live_at
cache_age
erro
```

Conteúdo de cache deve continuar no produto, mas a Action e o site precisam
dizer que o fórum não foi conferido ao vivo.

### Alto 3 — queda extrema que não chega a zero passa

**Arquivo/linhas:** `automacao/coletar.py:1433-1440`.

**Teste reproduzido**

Baseline:

```text
avisos=60, calendário=3, cronograma=3, itens_com_prazo=15
```

Leitura:

```text
avisos=1, calendário=1, cronograma=1, itens_com_prazo=1
```

Resultado: `(True, [])`.

A regra detecta somente transição positiva → zero. Perder 59 de 60 avisos ou
dois de três cursos com cronograma não produz alerta.

**Correção sugerida:** contratos por curso e por fonte, não apenas totais.
Queda relativa grande deve ser degradada/confirmada contra uma segunda leitura,
com tolerância explícita para mudança de bimestre.

---

## 5. Frescor

### Alto 4 — o aviso de três horas é estático e não envelhece

**Arquivo/linhas:** `automacao/render.py:465-495`, `516+`.

**Teste reproduzido**

Ao gerar o site com `checked_at=agora`, `frescor()` retornou banner vazio. O
HTML resultante não contém `Date.now`, temporizador ou outra lógica cliente.
Três horas depois, o arquivo continua exatamente igual: o banner não surge
sozinho.

As releituras reduzem a janela de erro durante o dia, mas não implementam a
promessa “a página avisa quando o retrato passa de três horas”. A janela
noturna entre 20h e 8h é especialmente relevante.

**Correção sugerida:** renderizar sempre os dados de tempo em atributos e
calcular a idade no navegador, inclusive ao retornar à aba. Alternativamente,
mostrar sempre a idade/horário e nunca afirmar dinamicamente que o retrato está
fresco.

### Alto 5 — falha atualiza o relógio de um retrato antigo

**Arquivo/linhas:** `automacao/coletar.py:1515-1519`,
`1527-1535`.

**Teste reproduzido**

Um snapshot antigo foi preservado após falha de fontes, mas `checked_at` foi
substituído pela hora da tentativa. O conteúdo velho passou a se apresentar
como se tivesse sido lido agora.

**Correção sugerida:** manter:

- `snapshot_at`: quando o conteúdo preservado foi realmente lido;
- `attempted_at`: quando a nova tentativa falhou;
- `source_status`: quais fontes falharam.

O cálculo de frescor deve usar `snapshot_at`.

---

## 6. SMTP

### O que segurou

Com `SMTP()` lançando `OSError("smtp fora")`:

```text
::error::Nao consegui enviar o e-mail: smtp fora
retorno = 1
```

O `continue-on-error` foi removido. A pane real de transporte agora deixa a
Action vermelha.

### Alto 6 — configuração ausente ainda é sucesso

**Arquivo/linhas:** `automacao/enviar_email.py:208-220`.

Sem `SMTP_HOST`, usuário, senha ou destinatário:

```text
E-mail nao configurado (faltam Secrets). Sigo sem enviar.
retorno = 0
```

Remover, renomear ou esvaziar um Secret faz o e-mail parar e mantém o workflow
verde.

**Correção sugerida:** no ambiente de CI, falta de configuração deve retornar
2. Se for desejável permitir execução local sem e-mail, usar flag explícita
`EMAIL_OPCIONAL=1`, nunca inferir opcionalidade pela ausência do Secret.

### Alto 7 — atraso do agendador pode suprimir o e-mail da manhã

**Arquivo/linhas:** `.github/workflows/guia-diario.yml:84-98`.

O workflow decide enviar pelo relógio real do runner:

```sh
HORA=$(date -u +%H)
HORA=11 → envia
HORA=12 → não envia
```

Se a execução agendada para 11 UTC começar depois das 12 UTC, situação possível
em agendadores compartilhados, o único e-mail diário é pulado.

**Correção sugerida:** distinguir a agenda que disparou usando
`${{ github.event.schedule }}` ou separar a execução matinal em workflow próprio.

---

## 7. Escrita interrompida

### O que segurou

Foi provocada uma exceção imediatamente antes de `Path.replace()`:

```text
conteúdo original = {"old": 1}
conteúdo após falha = {"old": 1}
arquivo .tmp = presente
```

O JSON principal não ficou truncado. A alteração foi efetiva para um único
arquivo.

### Médio 8 — atomicidade não cobre todo o snapshot

**Arquivos/linhas:** `automacao/coletar.py:1463-1472`,
`1552-1553`; `automacao/render.py:513`.

Ressalvas:

- `data.json` e `estado.json` são substituídos separadamente; queda entre os
  dois deixa dados novos com cache antigo;
- `index.html` ainda usa `write_text()` direto e pode ficar truncado;
- uma falha antes do `replace` deixa o `.tmp`;
- `carregar()` continua tratando JSON corrompido como ausente, sem registrar o
  diagnóstico.

O `concurrency.group` do workflow reduz colisões entre Actions, o que está
correto. A correção restante é fazer o snapshot inteiro possuir um ID/manifesto
e publicar somente depois de todos os arquivos validados.

---

## 8. Identidade

### O que segurou

Dois itens com o mesmo rótulo e `cmid` diferentes não mascararam a conclusão.
O teste versionado cobre esse caso.

### Médio 9 — fallback textual e tipo do ID ainda quebram identidade

**Arquivo/linhas:** `automacao/coletar.py:1484-1501`.

Casos reproduzidos:

1. dois itens sem `cmid`, mesmo rótulo, um deles muda de pendente para
   concluído → `novidades()` devolve lista vazia;
2. `cmid=1` no anterior e `cmid="1"` no atual → a conclusão vira
   `kind="novo"`.

**Correção sugerida:** normalizar sempre para string e não aceitar fallback
silencioso. Item sem ID deve receber uma identidade composta
`course_id + section_id + URL`, marcada como degradada.

---

## 9. Publicação

### O que segurou

- O passo `Publicar mudanças` vem antes do SMTP.
- Falha de `git push` interrompe o job antes do e-mail, pois o shell usa
  `-e` e não há `continue-on-error`.
- A Action `30177755648` executou coleta, fez push e depois enviou o e-mail.
- O Pages terminou construído e o site público serviu o commit mais recente.

### Alto 10 — “push concluído” ainda não significa “site publicado”

**Arquivo/linhas:** `.github/workflows/guia-diario.yml:66-98`.

Na execução observada:

- push terminou por volta de 22:35:02 UTC;
- e-mail foi enviado às 22:35:03 UTC;
- builds do Pages associados à sequência terminaram entre 22:35:34 e
  22:36:21 UTC.

O workflow não consulta o deploy do Pages. Assim, o e-mail ainda pode chegar
antes do site novo — e pode ser enviado mesmo se o Pages falhar depois.

**Correção sugerida:** depois do push, aguardar o build/deploy correspondente
ao commit ou usar um `snapshot_id` verificável no site. Só então enviar o
e-mail.

---

## 10. Cobertura dos testes

As suítes `test_prazos.py`, `test_login.py` e a compilação de `automacao/`
passaram. Os testes novos cobrem apenas o caminho feliz de cada correção.

Casos que precisam entrar:

1. duas perdas totais consecutivas continuam falhando fechado;
2. fonte offline com cache é marcada `cache`, não `live`;
3. queda 60→1 de avisos é detectada;
4. snapshot preservado não altera `snapshot_at`;
5. banner de frescor aparece no navegador depois de três horas sem novo build;
6. ausência de cada Secret SMTP retorna falha no CI;
7. agenda das 11 UTC atrasada ainda envia o e-mail matinal;
8. interrupção entre `data.json`, `estado.json` e `index.html`;
9. item sem `cmid` e mudança de tipo numérico/textual;
10. e-mail só é liberado após confirmação do Pages;
11. recado que cita atividade concluída é automaticamente recolhido.

---

## 11. O que está correto

- AVA e fila automática pública concordaram sobre o Quiz 1 do Módulo 2.
- O site refletiu as conclusões recentes após a nova coleta.
- O prazo do Módulo 4 e a cadeia de desbloqueio permaneceram separados.
- A telemetria mostrou 4 cursos, 36 seções, 62 itens, 60 avisos, 3 eventos,
  3 cronogramas e 12 itens com prazo.
- A COM170 não recebeu mais o cronograma regular como fallback.
- Exceção real de SMTP retorna código 1.
- `git push` precede a tentativa de e-mail.
- A substituição atômica preserva o JSON antigo quando falha antes do replace.
- A identidade por `cmid` funciona no formato normal observado no Moodle.
- O workflow possui grupo de concorrência.
- O Pages estava construído e o site respondia.
- Nenhum dado do AVA foi alterado durante os testes.
- Nenhuma correção foi aplicada nesta auditoria; somente este relatório foi
  criado.

## 12. Limite desta fase

Esta fase imediata não pode homologar o agendamento. Ainda é necessário observar
execuções reais pelo evento `schedule`, especialmente a das 8h, e acompanhar
por vários dias entrega do e-mail, heartbeat, atraso do runner e coerência do
site. Até agora, o histórico consultado continua composto por
`workflow_dispatch`.
