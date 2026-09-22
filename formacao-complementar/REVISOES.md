# Revisões

> Revisar não é reler. Reler dá a sensação de saber, e é justamente a sensação que engana.
> Revisar é **tentar lembrar antes de olhar**.

## Como funciona

Cada tema estudado gera três revisões:

| Quando | O que fazer | Tempo |
|---|---|---|
| **D+1** | Recitar os flashcards do módulo de memória. Depois conferir | 10 min |
| **D+7** | Responder as perguntas de revisão do módulo sem consultar. Depois conferir | 20 min |
| **D+30** | Refazer um exercício de nível 3 do módulo, do zero, sem olhar o que escreveu antes | 40 min |

**A regra:** tente lembrar **antes** de abrir o material. Se errar, tudo bem, errar consolida.
Se abrir o material primeiro, a revisão não vale nada.

## Fila de revisões

| Tema | Módulo | Estudei em | D+1 | D+7 | D+30 |
|---|---|---|---|---|---|
| | | | | | |

Preencha uma linha por tema ao terminar de estudar. Marque com `x` quando fizer.

## Provas cumulativas

A cada 4 módulos, uma prova que cobre **tudo desde o começo**, não só os 4 últimos.
Isso é de propósito: o módulo 01 precisa continuar vivo na semana 30.

| Prova | Cobre | Agendada | Feita | Nota |
|---|---|---|---|---|
| Cumulativa 1 | Módulos 00, 01, 04, 03 | | | |
| Cumulativa 2 | Tudo até 08 | | | |
| Cumulativa 3 | Tudo até 13 | | | |
| Cumulativa 4 | Tudo até 16 | | | |
| Cumulativa 5 | Tudo até 24 | | | |
| Cumulativa 6 | Tudo | | | |

## Flashcards acumulados

Os cartões de cada módulo vão sendo acrescentados aqui, e a revisão D+1 puxa
de **todos**, não só do módulo atual.

### Módulo 01: Python

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
default silencioso -> esconde erro. "1.234,56" vira 0.0 sem avisar
```

## Perguntas cumulativas

Perguntas que reaparecem em toda revisão, de qualquer módulo. São as que caem em entrevista.

1. Mutável vs imutável, com exemplo inventado na hora
2. Por que `except:` sozinho é perigoso
3. O que `os.replace` garante que `open("w")` não garante
4. Diferença entre autenticação e autorização
5. O que é um embedding e por que texto vira número
6. O que é RAG e que problema resolve
7. O que é function calling e por que existe
8. Quando **não** usar um agente
9. O que é RLS e por que existe se o app já filtra
10. Como você sabe que entende o código que a IA escreveu com você
