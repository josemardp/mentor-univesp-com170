# Módulo 01: Python

> Duração: 3 semanas na velocidade Padrão (8 a 10h/semana)
> Estudo de caso: `C:\projetos\central-compras` (somente leitura, nunca edite)
> Pré-requisito de saída: nota 4 no `MAPA_DE_COMPETENCIAS.md`

---

## 1. Objetivos

Ao terminar este módulo, com IA desligada, você consegue:

1. Explicar a diferença entre mutável e imutável, e prever o efeito em código real
2. Escrever função com type hints que outra pessoa entende sem perguntar
3. Usar `try/except` sem engolir erro em silêncio
4. Ler e escrever arquivo (texto, JSON, CSV, YAML) com encoding correto
5. Explicar o que é um decorador e escrever um
6. Explicar o que é um context manager e escrever um
7. Ler as 7.949 linhas do `central_compras.py` sem se perder
8. Defender em entrevista uma decisão de arquitetura que está nesse arquivo

**O objetivo não é "aprender Python".** Você já escreve Python que funciona. O objetivo é
fechar a distância entre o Python que existe nos seus projetos e o Python que você domina.

## 2. Pré-requisitos

- Python 3.11 ou superior instalado (`python --version`)
- VS Code
- Ter feito a prova do Módulo 00

Verificação rápida, no PowerShell:

```powershell
python --version
python -c "print('ok')"
```

## 3. Explicação conceitual

Python tem uma característica que causa mais bug em código real do que qualquer outra:
**variável em Python não é uma caixa, é uma etiqueta.**

Em linguagens como C, `x = 5` reserva um espaço de memória chamado `x` e põe 5 lá dentro.
Em Python, `x = 5` cria o número 5 em algum lugar e **cola a etiqueta `x` nele**.

Quando você faz `y = x`, não copia nada. Só cola uma segunda etiqueta no mesmo objeto.

O que acontece depois depende de uma coisa só: **se o objeto pode ser modificado ou não.**

- **Imutável** (int, float, str, tuple): não pode ser modificado. `y += 1` cria um objeto
  novo e move a etiqueta `y` para ele. `x` continua no antigo. Parece cópia, e o efeito é o mesmo.
- **Mutável** (list, dict, set): pode ser modificado. `y.append(4)` modifica o objeto em si.
  A etiqueta `x` está no mesmo objeto, então `x` "muda junto". Não mudou nada: é o mesmo objeto,
  visto por dois nomes.

Isso é a questão A2 da sua prova diagnóstica, e é a causa de uma família inteira de bugs
que só aparecem em produção.

## 4. Analogia simples

Pense num processo administrativo físico, na Companhia.

**Imutável é a data de um documento.** Se você precisa de outra data, você não rasura: emite
outro documento. O primeiro continua lá, intacto. Quem tinha cópia dele continua com a data antiga.

**Mutável é a pasta do processo.** Se o Sargento põe uma folha nova na pasta e você tem
o mesmo número de processo anotado, quando você for buscar, a folha nova está lá. Vocês dois
não têm cópias da pasta. Vocês têm o mesmo número de pasta anotado no bloquinho.

```python
# bloquinho do Josemar: processo 42
processo_josemar = ["capa", "despacho"]
# bloquinho do Sargento: mesmo processo 42
processo_sargento = processo_josemar

processo_sargento.append("anexo")   # sargento pôs folha na pasta

print(processo_josemar)   # ['capa', 'despacho', 'anexo']  <- apareceu na sua também
```

Nada foi copiado. Existe **uma pasta** e **dois bloquinhos** com o mesmo número.

Para ter uma pasta de verdade separada, tem que fotocopiar explicitamente:

```python
processo_sargento = processo_josemar.copy()   # agora sim, pasta nova
```

## 5. Explicação técnica

### 5.1 Identidade, igualdade e cópia

```python
a = [1, 2, 3]
b = a
c = a.copy()

a == b   # True  (mesmo conteúdo)
a is b   # True  (mesmo objeto na memória)
a == c   # True  (mesmo conteúdo)
a is c   # False (objeto diferente)
```

`==` compara conteúdo. `is` compara identidade. **Nunca use `is` para comparar valores**,
só para `None`: `if x is None`.

`copy()` é cópia rasa: copia o primeiro nível. Se a lista contém dicionários, os dicionários
continuam compartilhados. Para cópia profunda: `copy.deepcopy()`. O `central_compras.py`
importa `copy` justamente por isso.

### 5.2 A armadilha do argumento padrão mutável

```python
def adicionar(item, lista=[]):     # ERRADO
    lista.append(item)
    return lista

adicionar("a")   # ['a']
adicionar("b")   # ['a', 'b']   <- a lista sobreviveu entre chamadas
```

O padrão é avaliado **uma vez**, quando a função é definida, não a cada chamada.
O jeito certo:

```python
def adicionar(item, lista=None):
    if lista is None:
        lista = []
    lista.append(item)
    return lista
```

### 5.3 Type hints

```python
def quote_float(value: Any, default: float = 0.0) -> float:
```

Python **não verifica** isso em tempo de execução. Type hint é documentação que ferramenta
consegue ler (VS Code, mypy). Serve para você e para quem lê, não para o interpretador.

Sintaxe moderna (Python 3.10+), que é a usada no seu projeto:

```python
dict[str, Any]          # dicionário de string para qualquer coisa
list[Path]              # lista de Path
str | None              # string ou None (o antigo Optional[str])
dict[str, Any] | None   # dicionário ou None
```

A primeira linha do `central_compras.py` é `from __future__ import annotations`. Isso faz o
Python tratar todo type hint como texto, sem avaliar. Permite usar sintaxe nova em versão
antiga e evita custo de importação.

### 5.4 Exceções

```python
try:
    numero = float(valor)
except ValueError:          # específico, não `except:`
    return default
```

Três regras que separam código profissional de código de tutorial:

1. **Capture a exceção específica.** `except:` pega até `Ctrl+C` do usuário
2. **Nunca engula em silêncio.** `except: pass` é como desligar o alarme de incêndio
3. **`finally` sempre roda**, com ou sem erro. É onde vai a limpeza

No seu código tem um caso avançado, em `atomic_write_text`:

```python
except BaseException:
    temporario.unlink(missing_ok=True)
    raise
```

`BaseException` é mais amplo que `Exception`: pega `KeyboardInterrupt` e `SystemExit` também.
Faz sentido **aqui** porque a limpeza do arquivo temporário precisa acontecer mesmo se você
apertar Ctrl+C. E o `raise` no fim relança o erro, sem engolir. Esse par (limpar + relançar)
é o padrão correto.

### 5.5 Context manager

Serve para garantir que algo aconteça na saída, com erro ou sem.

```python
with open("arquivo.txt", encoding="utf-8") as f:
    texto = f.read()
# o arquivo é fechado aqui, mesmo se o read explodir
```

Escrever o seu:

```python
import contextlib

@contextlib.contextmanager
def cronometro(nome):
    inicio = time.time()
    try:
        yield                          # aqui roda o bloco do `with`
    finally:
        print(f"{nome}: {time.time() - inicio:.2f}s")

with cronometro("cálculo"):
    fazer_conta()
```

O `yield` divide a função em duas: o que roda antes do bloco e o que roda depois.
No seu projeto, `project_lock` usa isso para garantir que o arquivo de trava seja liberado
mesmo se o comando falhar no meio.

### 5.6 Decorador

Função que embrulha outra função para acrescentar comportamento.

```python
import functools

def logado(func):
    @functools.wraps(func)            # preserva nome e docstring da original
    def wrapped(*args, **kwargs):
        print(f"chamando {func.__name__}")
        return func(*args, **kwargs)
    return wrapped

@logado
def somar(a, b):
    return a + b
```

`@functools.wraps` não é opcional. Sem ele, `somar.__name__` vira `"wrapped"` e todo
rastreamento de erro e ferramenta de documentação quebra.

### 5.7 Arquivo e encoding no Windows

```python
with open(caminho, "w", encoding="utf-8", newline="") as f:
```

Duas coisas que só importam no Windows e que estão no seu código:

- **`encoding="utf-8"` é obrigatório.** Sem ele, Python no Windows usa cp1252 e acento quebra
- **`newline=""`** impede o Python de converter `\n` em `\r\n`. Sem isso, um CSV escrito no
  Windows e lido no Linux vem com linha em branco entre cada registro

## 6. Exemplos, lidos do seu próprio código

### Exemplo 1: validação defensiva

`central-compras/scripts/central_compras.py`, linha 1090:

```python
def quote_float(value: Any, default: float = 0.0) -> float:
    if value in {None, ""}:
        return default
    try:
        numero = float(str(value).replace(",", "."))
    except ValueError:
        return default
    if math.isnan(numero) or math.isinf(numero):
        return default
    return numero
```

O que essa função ensina:

- `str(value)` antes de `float()`: aceita número ou texto sem quebrar
- `.replace(",", ".")`: converte vírgula decimal (`"10,50"`) para o ponto que o `float()` espera
- `{None, ""}`: conjunto literal, mais rápido que `value == None or value == ""`
- **A parte que quase ninguém escreve:** `NaN` e infinito são floats válidos. `float("nan")`
  não levanta erro. E toda comparação com `NaN` é falsa, inclusive `NaN == NaN`. Se um `NaN`
  entra num ranking, ele contamina em silêncio: nenhuma comparação funciona e o resultado
  sai errado sem erro nenhum

O comentário original no arquivo diz exatamente isso. Leia o comentário no código: ele
explica o **porquê**, não o **o quê**. É assim que se comenta.

**O limite dessa função, que eu descobri rodando e não lendo.** Ela trata vírgula decimal,
mas **não trata separador de milhar**:

```python
quote_float("10,50")      # 10.5     certo
quote_float("1.234,56")   # 0.0      silenciosamente errado
```

Porque `"1.234,56".replace(",", ".")` vira `"1.234.56"`, que não é float válido, cai no
`except ValueError` e volta como `default`. **Não levanta erro. Devolve zero.**

Essa é a lição mais importante do módulo, e não está escrita em lugar nenhum do código:

1. Uma função defensiva que devolve `default` em vez de erro **esconde o problema**.
   Aqui um preço de R$ 1.234,56 virou R$ 0,00 no ranking, sem uma linha de log
2. Eu li essa função com atenção e não percebi. **Só apareceu quando rodei.** Ler não basta
3. `[não verificado]` se isso é bug de verdade no seu projeto ou se os dados nunca chegam
   com ponto de milhar. Provavelmente é o segundo caso, e aí a função está correta para o
   contrato dela. **Mas o contrato não está escrito em lugar nenhum.** Ninguém que leia essa
   função sabe que ela assume dado já normalizado

Guarde esse caso. Ele é a sua melhor resposta para "você já achou um bug lendo código?"
e para "qual o risco de programar com IA?".

### Exemplo 2: escrita atômica

Linha 341, resumida:

```python
def atomic_write_text(path: Path, text: str) -> None:
    """Grava por arquivo temporario e troca de uma vez so."""
    temporario = path.with_name(f".{path.name}.{os.getpid()}.{next(_TEMP_SEQ)}.tmp")
    try:
        with temporario.open("w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporario, path)
    except BaseException:
        temporario.unlink(missing_ok=True)
        raise
```

O problema que resolve: abrir em modo `"w"` **apaga o arquivo antes de escrever**. Se der
Ctrl+C no meio, você fica com um arquivo vazio e perdeu a série histórica inteira.

A solução: escreve num temporário, força para o disco (`fsync`), e só então troca de nome.
`os.replace` é atômico: ou o arquivo antigo está lá, ou o novo. Nunca meio.

O nome do temporário inclui `os.getpid()` porque dois comandos rodando ao mesmo tempo com
nome fixo escreviam no mesmo arquivo.

**Esta função é a sua melhor resposta de entrevista para "me fala de um problema difícil
que você resolveu".** Se você entender ela de verdade. Ver seção 15.

### Exemplo 3: decorador com contextvars

Linha 932:

```python
def read_session(func):
    """Reutiliza leituras dentro de uma operacao; nunca entre requests/threads."""
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if _READ_CACHE.get() is not None:
            return func(*args, **kwargs)
        token = _READ_CACHE.set({})
        try:
            return func(*args, **kwargs)
        finally:
            _READ_CACHE.reset(token)
    return wrapped
```

Cache de leitura que vale só dentro de uma operação. `contextvars` é como uma variável global
que **não vaza entre threads**. O `token` permite restaurar o estado anterior, então o
decorador pode ser aninhado sem estragar o cache de fora.

Isso é Python avançado. Se você não escreveu, precisa pelo menos saber ler.

## 7. Laboratório guiado

Arquivo: `laboratorios/lab01_guiado.py`. Siga os comentários, na ordem, rodando a cada passo.

```powershell
python C:\projetos\mentor-univesp\formacao-complementar\01-python\laboratorios\lab01_guiado.py
```

## 8. Laboratório sem tutorial

Arquivo: `laboratorios/lab02_sem_tutorial.py`. Só tem o enunciado e os testes.
**Você escreve o código.** Rode até os testes passarem.

**IA proibida neste laboratório.** Documentação oficial do Python liberada.

## 9. Exercícios

### Nível 1 (pode consultar material)
1. Escreva uma função que recebe uma lista de preços em texto brasileiro (`"1.234,56"`) e devolve a soma como float
2. Escreva uma função que recebe um dicionário e devolve uma cópia com todas as chaves em maiúsculas
3. Escreva uma função que lê um arquivo de texto e conta quantas linhas não estão vazias

### Nível 2 (documentação sim, IA não)
4. Escreva um context manager que mede tempo e imprime só se passar de 1 segundo
5. Escreva um decorador `@repetir(3)` que tenta a função até 3 vezes se ela levantar exceção
6. Escreva uma função que lê CSV com `csv.DictReader` e devolve lista de dicionários, tratando arquivo inexistente

### Nível 3 (sozinho, do zero)
7. Reimplemente `quote_float` de memória, sem olhar. Depois compare com o original
8. Reimplemente `atomic_write_text` de memória. Depois compare
9. Escreva uma função que recebe uma lista de cotações e devolve a de menor custo total, tratando lista vazia, preço ausente e preço inválido

### Nível 4 (depurar código quebrado)
10. Arquivo `laboratorios/lab03_bugs.py`. Tem 6 bugs plantados. Ache e corrija todos

### Nível 5 (explicar)
11. Grave um áudio de 2 minutos explicando o que `atomic_write_text` faz e por quê. Ouça depois
12. Escreva um parágrafo explicando `read_session` para alguém que não conhece `contextvars`

### Nível 6 (entrevista)
13. Ver seção 15

## 10. Perguntas de revisão

1. Qual a diferença entre `==` e `is`?
2. Por que `def f(lista=[])` é uma armadilha?
3. O que `from __future__ import annotations` faz?
4. Por que `except:` sozinho é perigoso?
5. Qual a diferença entre `Exception` e `BaseException`?
6. O que `@functools.wraps` preserva? O que quebra sem ele?
7. Por que `newline=""` ao escrever CSV no Windows?
8. O que `os.replace` garante que um `open("w")` não garante?
9. Por que `float("nan") == float("nan")` é `False`?
10. Qual a diferença entre `copy()` e `deepcopy()`?

## 11. Quiz

*(Uma resposta certa por questão. Gabarito em `laboratorios/quiz_gabarito.md`, só abra depois.)*

**Q1.** `a = [1,2]; b = a; b.append(3); print(a)` imprime:
(a) `[1,2]` (b) `[1,2,3]` (c) erro (d) `[3]`

**Q2.** `x = "abc"; y = x; y += "d"; print(x)` imprime:
(a) `abc` (b) `abcd` (c) erro (d) `d`

**Q3.** `except BaseException` pega `KeyboardInterrupt`?
(a) sim (b) não (c) só no Windows (d) só com `raise`

**Q4.** Sem `@functools.wraps`, o que quebra?
(a) nada (b) `func.__name__` (c) o retorno (d) os argumentos

**Q5.** `dict[str, Any] | None` significa:
(a) dicionário ou None (b) dicionário de None (c) erro em 3.11 (d) dicionário obrigatório

**Q6.** `os.replace` é atômico em:
(a) só POSIX (b) só Windows (c) ambos (d) nenhum

**Q7.** Para comparar com `None`, o correto é:
(a) `x == None` (b) `x is None` (c) `x.isNone()` (d) `not x`

**Q8.** Argumento padrão mutável é avaliado:
(a) a cada chamada (b) uma vez, na definição (c) nunca (d) na primeira chamada

**Q9.** `copy()` numa lista de dicionários:
(a) copia tudo (b) copia só o primeiro nível (c) não copia nada (d) dá erro

**Q10.** No `with`, o código depois do `yield` de um context manager roda:
(a) nunca (b) só sem erro (c) sempre, se estiver no `finally` (d) só com erro

## 12. Desafio prático

Escreva um módulo `cotacoes.py` que:

1. Lê um CSV de cotações (colunas: `loja`, `preco`, `frete`, `prazo_dias`)
2. Valida cada linha: preço e frete numéricos, não negativos, não NaN, não infinito
3. Calcula custo total (preço + frete)
4. Devolve o ranking ordenado por custo total
5. Grava o resultado com escrita atômica
6. Trata: arquivo inexistente, CSV vazio, coluna faltando, valor inválido, preço brasileiro com vírgula

**Restrições:** só biblioteca padrão. Sem pandas. **Sem IA.**

Depois de pronto, compare a sua solução com a lógica real do `central_compras.py`.
Não copie: compare e anote as diferenças no `DIARIO_DE_ESTUDOS.md`.

## 13. Erros comuns

| Erro | Sintoma | Correção |
|---|---|---|
| Argumento padrão mutável | Lista cresce entre chamadas | `=None` e cria dentro |
| `except:` sozinho | Ctrl+C não funciona | Capture a exceção específica |
| `except: pass` | Bug some sem rastro | Logue ou relance |
| Esquecer `encoding="utf-8"` | Acento vira lixo no Windows | Sempre declare |
| Esquecer `newline=""` no CSV | Linha em branco entre registros | Sempre no Windows |
| `is` para comparar número | Funciona até 256, quebra depois | Use `==` |
| Cópia rasa achando que é profunda | Alteração vaza para o original | `deepcopy` quando aninhado |
| `open("w")` em arquivo importante | Arquivo vazio se travar no meio | Escrita atômica |
| Decorador sem `functools.wraps` | Nome e docstring somem | Sempre use |
| Não tratar NaN | Cálculo errado, sem erro | `math.isnan` antes de usar |

## 14. Checklist de domínio

Marque só o que consegue fazer **sem IA e sem consultar**:

- [ ] Explico mutável vs imutável com um exemplo que eu invento na hora
- [ ] Prevejo a saída de código que compartilha referência
- [ ] Escrevo função com type hints modernos sem lembrar da sintaxe errado
- [ ] Uso `try/except` capturando exceção específica
- [ ] Sei quando usar `BaseException` e por que é raro
- [ ] Escrevo um context manager com `@contextlib.contextmanager`
- [ ] Escrevo um decorador com `@functools.wraps`
- [ ] Leio e escrevo CSV, JSON e YAML sem consultar
- [ ] Explico por que `encoding` e `newline` importam no Windows
- [ ] Explico escrita atômica e por que `os.replace` resolve
- [ ] Abro o `central_compras.py` e entendo qualquer função que caia
- [ ] Explico 3 decisões de arquitetura daquele arquivo numa entrevista

**Menos de 10 marcados: não avance para o módulo 04.** Refaça os laboratórios.

## 15. Perguntas de entrevista

### P1. "Qual a diferença entre lista e tupla em Python?"

**30 segundos:** Lista é mutável, tupla não. Na prática uso tupla quando o conjunto não deve
mudar, como uma coordenada ou um retorno fixo de função, e lista quando vou acrescentar item.

**2 minutos:** Acrescente que tupla pode ser chave de dicionário e lista não, justamente
porque precisa ser hashável, e imutabilidade é o que garante isso. E que tupla é levemente
mais rápida e ocupa menos memória.

**Aprofundado:** Tupla é imutável no primeiro nível. `t = ([1,2], 3)` permite `t[0].append(4)`,
porque o que é imutável é a referência, não o objeto apontado. Por isso `hash(([1,2],3))`
levanta `TypeError`.

### P2. "O que é um decorador?"

**30 segundos:** É uma função que recebe outra função e devolve uma versão embrulhada, com
comportamento a mais. Uso para log, cache e retry sem poluir a função original.

**2 minutos:** Acrescente o `@functools.wraps` e por que ele não é opcional. Dê um exemplo
concreto: num projeto meu tem um decorador de cache de leitura que vale só dentro de uma
operação, usando `contextvars` para não vazar entre threads.

**Aprofundado:** Decorador com argumento precisa de mais um nível de função, porque
`@repetir(3)` é uma chamada que **devolve** o decorador. E decorador de método precisa
considerar `self` como primeiro argumento posicional.

### P3. "Me fala de um problema técnico difícil que você resolveu."

Esta é a pergunta E2 da sua prova. Aqui está a resposta que o seu código sustenta:

**2 minutos:** "Num projeto meu de apoio a decisão de compra, os dados ficam em CSV no disco.
Descobrimos que abrir o arquivo em modo de escrita apaga o conteúdo antes de escrever. Se o
processo morre no meio, por Ctrl+C ou disco cheio, o arquivo fica vazio e a série histórica
inteira se perde. A solução foi escrita atômica: grava num arquivo temporário, força para o
disco com `fsync`, e só então troca de nome com `os.replace`, que é atômico nos dois sistemas.
Ou o arquivo antigo está lá, ou o novo. Nunca um meio termo.

Apareceu um segundo problema depois: com nome fixo de temporário, dois comandos rodando ao
mesmo tempo escreviam no mesmo arquivo e um apagava o do outro. Resolvi pondo o PID do
processo e um contador no nome. E no Windows o `os.replace` falha com `PermissionError` se
outro processo tem o arquivo aberto, mesmo só para leitura, então tem retry com espera
crescente antes de desistir."

**A regra:** só conte essa história se você conseguir responder as perguntas de acompanhamento.
São elas: por que `fsync` e não só `flush`? O que acontece se o processo morrer entre o
`fsync` e o `replace`? Por que `BaseException` e não `Exception` no cleanup?

Se você não sabe responder essas três, **volte à seção 6 antes de usar essa história.**
Uma história que desmonta na segunda pergunta é pior que não ter história.

### P4. "Você usa IA para programar. Como eu sei que você entende o código?"

**Resposta honesta, que funciona melhor que a defensiva:**

"Usa sim, bastante. O que eu faço é separar duas coisas: o código que a IA me ajudou a
escrever e o código que eu consigo defender. Para fechar essa distância eu montei um plano
de estudo que pega decisões dos meus próprios projetos e me obriga a reimplementar sem
assistência. Pode me perguntar qualquer parte, e se eu não souber eu digo que não sei."

Isso funciona porque é verdade e porque quem entrevista já viu muito candidato fingindo.
**Só use se for verdade.** Ao fim deste curso, vai ser.

## 16. Flashcards

```
Mutável vs imutável -> lista/dict/set mudam; int/str/tuple não
a is b -> mesmo objeto | a == b -> mesmo conteúdo
def f(lista=[]) -> armadilha: padrão avaliado UMA vez
str | None -> sintaxe 3.10+ para Optional[str]
from __future__ import annotations -> type hint vira texto, não avalia
except: -> pega até Ctrl+C. Sempre especifique
BaseException -> Exception + KeyboardInterrupt + SystemExit
functools.wraps -> preserva __name__ e __doc__ no decorador
contextlib.contextmanager -> antes do yield / depois do yield
encoding="utf-8" -> obrigatório no Windows, senão cp1252
newline="" -> evita \r\n duplicado no CSV
os.replace -> troca atômica, POSIX e Windows
fsync -> força do buffer do SO para o disco físico
NaN == NaN -> False. Toda comparação com NaN é falsa
copy() -> rasa | deepcopy() -> profunda
```

## 17. Mini projeto

O desafio da seção 12 **é** o mini projeto. Quando terminar, ele vira a base do módulo 08
(FastAPI): você vai expor esse ranking como API REST.

## 18. Estudo de caso: quais dos meus projetos

| Projeto | O que este módulo usa dele | Leitura obrigatória |
|---|---|---|
| **Central de Compras** | Estudo de caso principal. Python stdlib puro, sem framework escondendo nada | `scripts/central_compras.py`, linhas 341 a 378, 932 a 945, 1090 a 1104 |
| **Automação Univesp** | Organização de projeto: pacote com `dominio/`, `fontes/`, `pipeline.py`. Contraste com o arquivo único de 7.949 linhas | `automacao/pipeline.py` (862 linhas) |
| SecretárioTask | Não usa Python | |
| Esdra Cosméticos | Não usa Python | |
| FinanceiroJE | Não usa Python | |

**Exercício de arquitetura, para o fim do módulo:** os dois projetos Python são do mesmo autor
e resolvem problemas de porte parecido. Um é um arquivo de 7.949 linhas. O outro é um pacote
com 50 arquivos organizados por responsabilidade.

Qual está certo? Escreva meia página defendendo cada lado, e depois a sua posição.
Isso é a questão D2 da sua prova diagnóstica, e vai cair em entrevista.

**Lembrete:** os dois projetos são somente leitura. Se precisar mexer para experimentar,
copie o trecho para `laboratorios/`.
