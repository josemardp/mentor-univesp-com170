# Gabarito do quiz (Módulo 01)

> Só abra depois de responder as 10. Responder olhando aqui não mede nada.

| # | Resposta | Por quê |
|---|---|---|
| Q1 | **(b) `[1,2,3]`** | `b = a` não copia. As duas etiquetas apontam para a mesma lista, que é mutável |
| Q2 | **(a) `abc`** | `str` é imutável. `y += "d"` cria objeto novo e move só a etiqueta `y` |
| Q3 | **(a) sim** | `KeyboardInterrupt` herda de `BaseException`, não de `Exception`. Por isso `except Exception` não pega Ctrl+C e `except BaseException` pega |
| Q4 | **(b) `func.__name__`** | Sem `wraps`, vira `"wrapped"`. Junto vão `__doc__`, `__module__` e a assinatura que as ferramentas leem |
| Q5 | **(a) dicionário ou None** | `\|` em type hint é união (3.10+). Equivale a `Optional[dict[str, Any]]` |
| Q6 | **(c) ambos** | É a razão de usar `os.replace` e não `os.rename`: `rename` não é atômico no Windows quando o destino existe |
| Q7 | **(b) `x is None`** | `None` é singleton. `==` pode ser sobrecarregado por `__eq__` e mentir. `not x` é diferente: `0`, `""` e `[]` também são falsos |
| Q8 | **(b) uma vez, na definição** | É a causa da armadilha do argumento padrão mutável |
| Q9 | **(b) copia só o primeiro nível** | A lista externa é nova, os dicionários dentro são os mesmos objetos. Para o segundo nível: `copy.deepcopy()` |
| Q10 | **(c) sempre, se estiver no `finally`** | Sem `finally`, uma exceção dentro do `with` pula o código depois do `yield`. Por isso todo context manager sério põe a limpeza no `finally` |

## Se errou

| Errou | Releia |
|---|---|
| Q1, Q2, Q9 | Seções 3, 4 e 5.1 |
| Q8 | Seção 5.2 |
| Q5 | Seção 5.3 |
| Q3 | Seção 5.4 |
| Q10 | Seção 5.5 |
| Q4 | Seção 5.6 |
| Q6 | Seção 6, exemplo 2 |
| Q7 | Seção 5.1 |

**3 erros ou mais: refaça o `lab01_guiado.py` antes de seguir.**
