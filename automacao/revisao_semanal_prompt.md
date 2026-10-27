Você está montando a revisão de prova da disciplina {disciplina}, semana {semana}, do curso da Univesp do Josemar. A pasta atual é a pasta dessa semana.

Leia primeiro `COBERTURA.md`, `manifest.json` e `GABARITO.md`. Depois leia **por inteiro** os arquivos de `fontes/` que terminam em `.txt`, nesta ordem:

1. `quiz-*.txt`: a revisão de cada tentativa do questionário, com a alternativa marcada, a nota, a resposta oficial e o comentário do AVA quando ele já os mostra.
2. `livro-*.txt`: o **texto-base** da semana, lido no leitor do AVA (Biblioteca Virtual ou Minha Biblioteca). É a leitura principal e a prova cobra detalhe dele. O título diz o capítulo, a seção ou as páginas pedidas; o arquivo pode trazer páginas a mais, do mesmo capítulo: concentre a revisão no trecho pedido e use o resto só como contexto.
3. `*.pdf.txt`: slides das videoaulas, textos de apoio e capítulos em PDF. Cada página começa com `[pág. N]`. Quando o título ou o cabeçalho diz quais páginas ler, a revisão é desse trecho.
4. `video-*.txt`: transcrição das videoaulas. O cabeçalho diz se é a legenda revisada da Univesp ou a automática do YouTube.
5. `pagina-*.txt` e `web-*.txt`: páginas do AVA (Início, Em síntese, Aprofundando) e páginas de fora do AVA que o material indica.

Escreva um único arquivo, `REVISAO.md`, nesta pasta. Não crie nem altere nenhum outro arquivo.

Estrutura do `REVISAO.md`:

1. `## {disciplina}, semana {semana}: <tema da semana>` e, logo abaixo, os objetivos da semana em até 5 linhas.
2. `### Conceitos-chave`: cada conceito com definição curta e a fonte entre parênteses (ex.: "texto-base, p. 17", "slides da videoaula 2", "página Em síntese"). Classificação, lista e enumeração do texto-base entram completas ("são quatro níveis: ...", "os oito princípios de ..."), porque a prova pergunta "quantos" e "qual não é".
3. `### Autores, siglas e exemplos citados`: **todos** os nomes de autor, sigla, obra, data e exemplo concreto que aparecem nas fontes, mesmo os que parecem secundários, cada um com uma linha dizendo o que defendem ou para que servem. A prova cobra detalhe.
4. `### Resumo por fonte`: um bloco por fonte (texto-base primeiro e mais detalhado, depois videoaulas, PDFs e páginas), com o que cada um ensina.
5. `### Questionário da semana`: cada questão distinta, na ordem do `GABARITO.md`, com o enunciado resumido, a alternativa certa e o porquê. **A resposta vem só do `GABARITO.md`**, e você diz de onde ela vem: "resposta oficial do AVA" ou "nota cheia na tentativa". Use o comentário do AVA quando houver e complete a explicação com as fontes, citando onde está. Se o `GABARITO.md` disser "sem gabarito do AVA ainda", escreva isso; pode indicar a alternativa que as fontes sustentam, sempre com `[VERIFICAR: sem gabarito do AVA]`, e cite as que o gabarito dá como erradas com certeza. Se o questionário estiver pendente, escreva isso e deixe a seção para a próxima rodada.
6. `### Pegadinhas`: onde é fácil confundir (conceitos parecidos, autores trocados, asserção verdadeira com justificativa falsa), começando pelas alternativas erradas do questionário que pareciam certas.
7. `### Questões de treino`: 8 questões inéditas no formato da prova da Univesp (asserção-razão com "PORQUE", "I, II e III, está correto o que se afirma em", completar lacunas, alternativa correta de A a E), baseadas só nas fontes. Dê prioridade ao que o questionário **não** cobriu, sobretudo o texto-base. O gabarito comentado vem depois de todas as questões, nunca junto delas.
8. `### Cobertura`: copie a tabela da `COBERTURA.md`.

Logo abaixo do título da seção 1, antes dos objetivos, ponha um quadro `> **Cobertura a completar:**` listando cada item marcado **NÃO LIDO**, **SEM LEGENDA**, **FALHOU**, **pendente**, **sem tentativa** ou **feito, mas o AVA não mostra a revisão** na `COBERTURA.md`, com o título completo (autor, capítulo e páginas quando o título trouxer). Diga qual situação impede afirmar que aquela fonte foi lida. Só escreva que a semana foi lida por inteiro quando todas as fontes estiverem lidas ou encaminhadas para uma fonte lida. Se não houver nada a completar, omita o quadro.

Regras:
- Use só o que está nas fontes. Não complete lacuna com conhecimento geral. Quando algo for incerto, marque `[VERIFICAR: ...]`.
- **Nunca** diga qual alternativa foi marcada, nem que uma questão foi acertada ou errada, sem que o `GABARITO.md` diga. Dedução sua sobre resposta é sempre `[VERIFICAR]`.
- A transcrição automática erra nome próprio (Durkheim pode virar "do carne"). Corrija pelo contexto dos slides e do texto-base e nunca cite frase da transcrição como fala literal de alguém. A legenda revisada da Univesp vem toda em maiúsculas: escreva normalmente.
- Fórmula vem em texto simples (3/4, a⁷, 8,5 × 10⁶). Mantenha assim, sem LaTeX.
- Nunca escreva que o material foi "conferido contra o AVA".
- Português do Brasil, direto, sem travessão (o caractere —). Use vírgula, dois-pontos ou frase nova no lugar.
- Não mencione a profissão do aluno nem dado pessoal dele.
