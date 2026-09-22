# Guia Instrucional — Estruturas de Repetição, Laços e Teste de Mesa
> **Subtítulo:** Domínio Definitivo da Lógica de Programação e Rastreamento de Algoritmos  
> **Disciplina de Referência:** COM100 — Pensamento Computacional (Univesp)  
> **Finalidade do Documento:** Material didático estruturado para estudo, geração de slides de apresentação e síntese no NotebookLM.

---

## Módulo 1: Visão Geral e Fundamentos do Controle de Fluxo

### 1.1 O que é o Fluxo de Execução de um Programa?
Por padrão, um computador executa instruções de forma **linear e sequencial**: lê a linha 1, executa; lê a linha 2, executa; e assim sucessivamente, de cima para baixo.

No entanto, problemas do mundo real raramente são lineares. Para resolver problemas complexos, precisamos de duas ferramentas fundamentais:
1. **Estruturas de Decisão (Seleção):** O computador decide qual caminho seguir com base em uma condição lógica (`Se ... Então ... Senão`).
2. **Estruturas de Repetição (Laços / *Loops* / Iterações):** O computador repete um mesmo bloco de instruções várias vezes, enquanto uma condição for verdadeira ou até que um objetivo seja atingido.

### 1.2 Por que precisamos de Laços de Repetição?
Imagine que você precise imprimir na tela os números de 1 a 1.000:
* **Sem repetição:** Você teria que escrever 1.000 linhas de comando `escreva(1)`, `escreva(2)`, etc. Isso gera código redundante, sujeito a erros e impossível de manter.
* **Com repetição:** Você escreve apenas 3 linhas de código, instruindo a máquina a contar de 1 até 1.000 automaticamente.

### 1.3 Os Três Elementos Fundamentais de Qualquer Laço
Todo laço de repetição no mundo precisa de três engrenagens para funcionar corretamente e não travar o computador em um **laço infinito** (*loop* infinito):

```
┌────────────────────────────────────────────────────────────────────────┐
│                   AS TRÊS ENGRENAGENS DE UM LAÇO                       │
├────────────────────────────────────────────────────────────────────────┤
│ 1. INICIALIZAÇÃO: Define onde a variável começa (ex.: x <- 1)          │
│ 2. CONDIÇÃO DE PARADA: Teste lógico que decide se continua (ex.: x <= 5)│
│ 3. ATUALIZAÇÃO (PASSO): Modifica a variável a cada volta (ex.: x <- x+1)│
└────────────────────────────────────────────────────────────────────────┘
```

1. **Inicialização:** A atribuição do valor de partida à **variável de controle** (ou variável contadora) antes de o laço começar.
2. **Condição de Teste / Parada:** Uma expressão lógica (que resulta em `VERDADEIRO` ou `FALSO`). Enquanto for verdadeira, o laço roda. Quando se torna falsa, o laço encerra.
3. **Passo / Incremento / Atualização:** A alteração obrigatória do valor da variável contadora dentro do laço. Sem isso, a condição nunca mudará e o programa rodará para sempre até travar a memória.

---

## Módulo 2: Anatomia das Três Estruturas de Repetição

A ciência da computação organiza os laços em três grandes categorias, diferenciadas pelo momento em que a condição lógica é testada:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    COMPARATIVO DAS ESTRUTURAS DE REPETIÇÃO                   │
├──────────────────────┬────────────────────────┬──────────────────────────────┤
│ Estrutura            │ Momento do Teste       │ Quantas vezes pode rodar?    │
├──────────────────────┼────────────────────────┼──────────────────────────────┤
│ 1. ENQUANTO (While)  │ NO INÍCIO (na entrada) │ De 0 a N vezes               │
│ 2. REPITA (Do-While) │ NO FIM (na saída)      │ De 1 a N vezes (mínimo 1)    │
│ 3. PARA (For)        │ CONTROLE INTEGRADO     │ Número fixo e pré-determinado│
└──────────────────────┴────────────────────────┴──────────────────────────────┘
```

---

### 2.1 A Estrutura `ENQUANTO ... FAÇA` (*While Loop*)

#### A Metáfora Didática: A Catraca do Cinema com o Segurança
Imagine uma catraca de cinema com um segurança na porta. Para entrar na sala, você precisa mostrar o ingresso válido:
* Se você tem o ingresso válido no bolso, ele deixa você entrar. Você assiste ao filme e, ao sair pela porta dos fundos, volta para a fila da catraca para checar novamente.
* **E se você já chegar à catraca SEM ingresso?** O segurança barra você **imediatamente no portão**! Você **NÃO ENTRA NENHUMA VEZ** na sala de cinema e vai direto para a rua.

#### Sintaxe em Pseudocódigo:
```text
enquanto (condicao_logica) faca
    // Bloco de instruções que será repetido
    // Atualização da variável de controle
fimenquanto
```

#### Regra de Ouro do `ENQUANTO`:
> ⚠️ **ATENÇÃO MÁXIMA PARA A PROVA:**  
> No `ENQUANTO`, o teste lógico é realizado **ANTES** de executar o bloco interno.  
> Se a condição for falsa logo na primeira avaliação, o corpo do laço **NÃO É EXECUTADO NENHUMA VEZ (ZERO VEZES)**.

---

### 2.2 A Estrutura `REPITA ... ATÉ QUE` (*Do-While Loop*)

#### A Metáfora Didática: O Restaurante por Quilo (Pague na Saída)
No restaurante por quilo, você entra, serve seu prato, senta e come primeiro. Apenas quando você termina de comer e caminha até a saída é que o caixa confere a comanda para verificar se a conta foi paga:
* Mesmo que você desista ou não tenha dinheiro, você **obrigatoriamente já entrou e consumiu pelo menos uma vez**.

#### Sintaxe em Pseudocódigo:
```text
repita
    // Bloco de instruções
    // Atualização da variável
ate (condicao_de_parada)
```

#### Regra de Ouro do `REPITA`:
> ⚠️ **ATENÇÃO MÁXIMA PARA A PROVA:**  
> No `REPITA`, o bloco de instruções é executado primeiro e o teste lógico só é feito **NO FINAL**.  
> Portanto, o bloco interno é executado **OBRIGATORIAMENTE PELO MENOS UMA VEZ**, mesmo que a condição já seja satisfeita logo de cara.

---

### 2.3 A Estrutura `PARA ... DE ... ATÉ` (*For Loop*)

#### A Metáfora Didática: A Corrida com Número Fixo de Voltas
O professor de educação física avisa: *"Dê exatamente 5 voltas na pista"*.  
Não há incerteza ou checagens complexas: há um número de repetições pré-fixado conhecido de antemão.

#### Sintaxe em Pseudocódigo:
```text
para variavel de valor_inicial ate valor_final [passo valor_passo] faca
    // Instruções repetidas
fimpara
```

* O próprio comando inicializa a variável, testa se chegou ao limite final e soma +1 (ou o passo indicado) automaticamente a cada volta.

---

## Módulo 3: O Método Infalível do Teste de Mesa (*Trace Table*)

### 3.1 O que é um Teste de Mesa?
O Teste de Mesa é a técnica manual em que o ser humano simula o papel do processador do computador. Utiliza-se uma tabela em papel ou tela para anotar o estado exato de cada variável linha por linha de código.

### 3.2 O Protocolo de 4 Passos para Resolver Questões de Algoritmo na Prova:
1. **Passo 1:** Desenhe colunas: uma para cada variável do programa e uma para a **Condição Lógica**.
2. **Passo 2:** Anote os valores iniciais das variáveis antes de o laço começar.
3. **Passo 3:** Na linha do `enquanto`, substitua a variável pelo seu número real e pergunte em voz alta: *"Isso é VERDADEIRO ou FALSO?"*.
4. **Passo 4:** Se for FALSO, trace uma linha riscando o laço e vá direto para a primeira linha após o `fimenquanto`.

---

## Módulo 4: Desmontando a Questão-Problema da Prova Passo a Passo

Vamos analisar exatamente o exercício que gerou a dúvida na aula:

### O Código sob Análise:
```text
Linha 1:  x <- 5
Linha 2:  total <- 0
Linha 3:  enquanto (x < 5) faca
Linha 4:     total <- total + x
Linha 5:     x <- x + 1
Linha 6:  fimenquanto
Linha 7:  escreva(total, x)
```

---

### Simulação Minuciosa Linha por Linha:

#### Momento 1: As Linhas 1 e 2 (Preparação do Terreno)
* O computador lê a **Linha 1**: `x <- 5`.  
  *Memória:* A caixinha da variável `x` recebe o valor **5**.
* O computador lê a **Linha 2**: `total <- 0`.  
  *Memória:* A caixinha da variável `total` recebe o valor **0**.

#### Momento 2: A Chegada na Catraca (Linha 3)
* O computador lê a **Linha 3**: `enquanto (x < 5) faca`.
* O processador substitui `x` pelo valor que está na memória:
  $$\text{Pergunta: } (5 < 5) \text{ ?}$$
* **Atenção Filosófica e Matemática:**  
  *O número 5 é menor do que 5?* **NÃO!** Cinco é rigorosamente igual a cinco. Portanto, a resposta lógica é **FALSO**!
* Como o resultado deu **FALSO logo na entrada**, o computador obedece à regra de ouro do `enquanto`:  
  👉 **ABORTA A ENTRADA NO LAÇO IMEDIATAMENTE!**

#### Momento 3: As Linhas 4, 5 e 6 (O Pulo do Gato)
* O computador **PULA POR CIMA** das linhas 4 e 5 sem executá-las!
  - A linha `total <- total + x` **NUNCA FOI LIDA**.
  - A linha `x <- x + 1` **NUNCA FOI LIDA**.
* O computador aterrissa diretamente na **Linha 7** (logo após o `fimenquanto`).

#### Momento 4: A Impressão na Tela (Linha 7)
* O computador lê a **Linha 7**: `escreva(total, x)`.
* Ele consulta a memória:
  - Quanto vale `total`? Continua valendo **0** (seu valor inicial da Linha 2).
  - Quanto vale `x`? Continua valendo **5** (seu valor inicial da Linha 1).
* **Resultado que aparece no monitor:** `0` e `5`.

---

### A Tabela do Teste de Mesa desta Questão:

| Passo | Linha Executada | Variável `x` | Variável `total` | Teste Lógico `(x < 5)` | Decisão do Processador |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | Linha 1 | **5** | - | - | Atribuição inicial |
| **2** | Linha 2 | 5 | **0** | - | Atribuição inicial |
| **3** | Linha 3 | 5 | 0 | **`5 < 5` $\rightarrow$ FALSO!** | **Barra a entrada e salta para a Linha 7** |
| **4** | Linha 7 | 5 | 0 | - | Imprime na tela: **0 e 5** |

---

## Módulo 5: E se a Banca mudasse uma única vírgula? (Estudo Comparativo)

Observe como uma mudança sutil no operador lógico altera completamente o resultado. Isso é o que a Univesp mais explora:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              COMPARAÇÃO: OPERADOR ESTRITO (<) vs OPERADOR COM IGUAL (<=)    │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ CENÁRIO A: com operador menor (<)    │ CENÁRIO B: com menor ou igual (<=)   │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ x <- 5                               │ x <- 5                               │
│ total <- 0                           │ total <- 0                           │
│ enquanto (x < 5) faca                │ enquanto (x <= 5) faca               │
│    total <- total + x                │    total <- total + x                │
│    x <- x + 1                        │    x <- x + 1                        │
│ fimenquanto                          │ fimenquanto                          │
│                                      │                                      │
│ • Teste: 5 < 5 é FALSO               │ • Volta 1: 5 <= 5 é VERDADEIRO!      │
│ • Roda: ZERO VEZES                   │   total vira 0 + 5 = 5               │
│ • Saída: total = 0 e x = 5           │   x vira 5 + 1 = 6                   │
│                                      │ • Volta 2: 6 <= 5 é FALSO! Sai.      │
│                                      │ • Roda: 1 VEZ                        │
│                                      │ • Saída: total = 5 e x = 6           │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

---

## Módulo 6: Exemplo Adicional Resolvido Passo a Passo

Vamos resolver o teste de fixação complementar para sedimentar o conhecimento:

### Algoritmo:
```text
1:  a <- 1
2:  soma <- 10
3:  enquanto (a < 3) faca
4:     soma <- soma + 2
5:     a <- a + 1
6:  fimenquanto
7:  escreva(soma, a)
```

### Rastreamento Completo:

* **Antes de entrar:** `a = 1`, `soma = 10`.
* **1ª Avaliação da Linha 3:** `1 < 3`? **SIM (Verdadeiro)!**
  - Entra no laço!
  - Linha 4: `soma <- 10 + 2` $\rightarrow$ `soma` passa a valer **12**.
  - Linha 5: `a <- 1 + 1` $\rightarrow$ `a` passa a valer **2**.
  - Chegou no `fimenquanto`? O computador é obrigado a voltar para a Linha 3!
* **2ª Avaliação da Linha 3:** `2 < 3`? **SIM (Verdadeiro)!**
  - Entra no laço pela segunda vez!
  - Linha 4: `soma <- 12 + 2` $\rightarrow$ `soma` passa a valer **14**.
  - Linha 5: `a <- 2 + 1` $\rightarrow$ `a` passa a valer **3**.
  - Chegou no `fimenquanto`? Volta para a Linha 3!
* **3ª Avaliação da Linha 3:** `3 < 3`? **NÃO (Falso)!**
  - O número 3 não é menor do que 3!
  - O laço encerra! O computador salta para a Linha 7.
* **Linha 7:** `escreva(soma, a)`.
  - Imprime na tela: **`14` e `3`**!

---

## Módulo 7: Tabela de Consulta Rápida das Pegadinhas de Prova

| Pegadinha da Banca | O que o estudante descuidado pensa | O que a lógica da máquina realmente faz |
| :--- | :--- | :--- |
| **Laço que não entra** | Acha que o laço sempre roda pelo menos uma vez. | No `enquanto`, se a condição for falsa na largada, roda **zero vezes**. |
| **Confundir `<` com `<=`** | Acha que `5 < 5` é verdadeiro. | `5 < 5` é **falso**; apenas `5 <= 5` é verdadeiro. |
| **Esquecer o incremento** | Não percebe a ausência da linha `x <- x + 1`. | O laço entra em *loop* infinito e nunca encerra. |
| **Teste de mesa no fim** | Acha que `repita` é idêntico a `enquanto`. | O `repita` sempre executa o bloco pelo menos uma vez antes de testar. |
| **Valor final da variável** | Acha que o contador termina com o valor que satisfez a condição. | O contador termina com o primeiro valor que **tornou a condição falsa**! |

---

## Módulo 8: Roteiro Estruturado para Geração de Slides no NotebookLM

Para você colar no NotebookLM e gerar sua apresentação de slides, utilize este roteiro temático:

* **Slide 1:** Título: *Desmistificando Laços de Repetição e Teste de Mesa em Algoritmos*.
* **Slide 2:** O Problema da Linearidade: Por que programas precisam tomar decisões e repetir tarefas?
* **Slide 3:** O Tripé de um Laço: Inicialização, Condição de Teste e Passo de Incremento.
* **Slide 4:** `Enquanto` (*While*): A metáfora da catraca e por que ele pode rodar ZERO vezes.
* **Slide 5:** `Repita` (*Do-While*): A metáfora do restaurante por quilo e a execução obrigatória de pelo menos UMA vez.
* **Slide 6:** `Para` (*For*): Repetições previsíveis com contadores determinados.
* **Slide 7:** O que é Teste de Mesa? A arte de rastrear variáveis na memória sem adivinhação.
* **Slide 8:** Análise de Caso Real da Univesp: O mistério de `x <- 5; enquanto (x < 5)`.
* **Slide 9:** A diferença crucial entre `<` (estrito) e `<=` (inclusivo) na contagem de voltas.
* **Slide 10:** Checklist de Ouro para a Prova Presencial: 5 regras para nunca errar rastreamento de código.
