Você vai destilar a revisão da semana {semana} de {disciplina} numa ficha curta para a apostila de prova do Josemar (Univesp). A pasta atual é a pasta da semana.

Leia `REVISAO.md` (revisão completa, sua única fonte de conteúdo) e `COBERTURA.md`. Escreva **um único arquivo**, `apostila.json`, nesta pasta. Não crie nem altere nenhum outro arquivo.

A apostila é para estudar para a prova presencial, que sai do mesmo banco dos questionários do AVA. É um **resumo**: a ficha inteira, sem as questões de treino, precisa caber em **uma página A4** impressa em duas colunas. Na medida exata: só o que ajuda a acertar questão. Nada de extrato completo, nada de repetir a mesma ideia em duas seções. Cada fato aparece uma vez, na seção onde ele rende mais. Na dúvida entre pôr e tirar, tire.

Já estão na apostila, em semanas anteriores, estes termos e autores. **Não repita.** Só volte a um deles se esta semana trouxer algo novo, e aí diga só o novo:
{ja_vistos}

Formato exato do `apostila.json` (JSON válido, UTF-8, sem comentários):

{{
  "tema": "tema da semana em até 8 palavras",
  "ideia_central": "a ideia que amarra a semana, até 25 palavras",
  "conceitos": [{{"termo": "...", "definicao": "até 20 palavras"}}],
  "autores": [{{"nome": "...", "referencia": "obra ou texto e ano, curto", "ideia": "o que defende, até 20 palavras"}}],
  "comparacoes": [{{"titulo": "...", "colunas": ["", "A", "B"], "linhas": [["critério", "...", "..."]]}}],
  "exemplos": [{{"exemplo": "exemplo concreto citado nas aulas ou slides", "explicacao": "o que ele ilustra, até 15 palavras"}}],
  "cobrado": ["afirmação correta que o questionário cobrou, até 20 palavras"],
  "pegadinhas": [{{"confusao": "o erro comum, até 15 palavras", "certo": "o certo, até 15 palavras"}}],
  "treino": [{{"enunciado": "...", "alternativas": ["...", "...", "...", "...", "..."], "correta": "A", "comentario": "por que, até 40 palavras"}}],
  "ler_por_conta": ["título completo do que ficou NÃO LIDO ou SEM LEGENDA na COBERTURA.md"]
}}

Limites: conceitos até 6; autores até 5 (os que a prova cobra, não todo nome citado); comparacoes até 1, com no máximo 5 linhas (só quando houver contraste que a prova explora, como dois autores ou duas concepções); exemplos até 3; cobrado até 5 (os mais prováveis na prova, sem repetir conceito já dito); pegadinhas até 3; treino **exatamente 4** questões inéditas no formato da prova da Univesp (asserção-razão com PORQUE, "I, II e III", lacunas, alternativa correta), com 5 alternativas cada e `correta` de "A" a "E". Lista vazia é permitida quando não houver o que pôr.

Estilo: português do Brasil, frases curtas e diretas. Pode usar `**negrito**` para o termo-chave dentro de uma frase, com parcimônia. Sem travessão (o caractere —), sem emoji, sem HTML. Não invente nada que não esteja na `REVISAO.md`; o que lá estiver marcado `[VERIFICAR]` fica de fora. Não mencione a profissão do aluno.
