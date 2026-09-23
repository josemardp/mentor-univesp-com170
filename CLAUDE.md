<!-- PROJECT-MENTOR:START v1 -->
## Mentor de Projetos (protocolo v1)

Este projeto é acompanhado pelo Mentor de Projetos. Slug: `mentor-univesp`. O estado executivo vive em `.project-mentor/project.yaml` e o histórico em `.project-mentor/sessions/`. **Nunca edite esses arquivos à mão**: toda escrita passa pelo CLI `mentor`.

Como achar o CLI (Windows): `%PROJECT_MENTOR_HOME%\bin\mentor.cmd`. Se a variável `PROJECT_MENTOR_HOME` não existir, procure a pasta `mentor-de-projetos` ao lado deste projeto e use `bin\mentor.cmd` de lá. Se ainda assim não conseguir executar comandos, siga a seção "Sem terminal".

### Início da sessão
1. Peça ao usuário para confirmar que fez `git pull` se ele trocou de computador.
2. Rode `mentor project mentor-univesp --brief` e leia a última sessão em `.project-mentor/sessions/`.
3. Apresente em até 8 linhas: onde paramos, última entrega, pendências, bloqueios, próxima ação. Não invente nada que não esteja no estado.
4. Pergunte o objetivo só se não estiver claro. Depois rode `mentor start mentor-univesp --objective "..." --agent <claude-code|codex|antigravity|copilot>`.

### Durante
- Nunca marque ação como concluída só porque um arquivo foi criado. Distinga **implementado** (código escrito), **testado** (teste executado com resultado) e **validado** (o usuário confirmou). Agente nunca marca "validado".
- Ação nova: `mentor action add mentor-univesp --title "..."`. Concluir: `mentor action done mentor-univesp <act-id> --level implemented|tested`. Bloqueio: `mentor blocker add mentor-univesp --description "..."`.
- Não altere estágio (`mentor stage`) sem o usuário pedir.

### Encerramento
Quando o usuário disser "encerrar", "fechar sessão", "terminei" ou invocar a skill de encerramento:
1. Escreva um rascunho em arquivo temporário (fora do repositório) com as seções: Resumo executivo · Concluído (prefixo `[implementado]`, `[testado]` ou `[validado]`, e `(act-NNN)` no fim quando for ação cadastrada) · Arquivos/áreas alteradas · Testes e resultados · Decisões · Pendências · Bloqueios · Riscos · Próxima ação recomendada. Máximo 60 linhas. Sem raciocínio interno, transcrição, segredos, dados pessoais de terceiros ou conteúdo de documentos policiais.
2. Rode `mentor close mentor-univesp --from <rascunho.md>` e mostre o resultado da validação. Se falhar, mostre o erro e **não** finja sucesso.
3. Avise se há arquivos de `.project-mentor/` a commitar e mostre o comando sugerido pelo CLI. Não execute commit/push sem autorização explícita nesta sessão.

### Sem terminal
Se você não puder executar comandos, gere o rascunho da sessão em `.project-mentor/pending-close.md` no formato do protocolo (mesmas seções acima, com frontmatter `agent:` e `objective:`) e peça ao usuário para rodar `mentor sync`. O `sync` importa o rascunho, grava a sessão e atualiza o estado; se o rascunho for inválido, nada é descartado e o erro aparece para correção.
<!-- PROJECT-MENTOR:END -->

## Este repositório é público (vitrine do LinkedIn)

Nada de coleta bruta do AVA, gabarito de questionário, nota, nome de colega ou dado pessoal/profissional entra no git. Isso vai para `privado/`, que é um atalho (junction) para `G:\Meu Drive\10_JOSEMAR_PESSOAL\03_PROJETOS_ATIVOS\02_TECNOLOGIA_E_IA\mentor-univesp-privado`, criado pelo `automacao/configurar_local.ps1` e ignorado pelo git. Dentro de `privado/` vale a mesma árvore de pastas do repositório.

## Três frentes neste repositório

| Pasta | O que é | Quando entrar |
|---|---|---|
| `automacao/`, `docs/`, `references/` | Robô que lê o AVA e gera o guia diário | Prazos, avisos, painel |
| `estudo/` | Revisão para as provas presenciais da Univesp. Uma pasta por bimestre (`2026-3bim/`), ferramentas em `estudo/ferramentas/` (`assimilar.py status` mostra a prontidão, o IPP) | "vamos estudar para a prova", simulado, apostila |
| `formacao-complementar/` | Trilha técnica pessoal em IA e automação, módulos 00 a 29. **Só entrar quando ele chamar** ("vamos estudar a formação") e começar pelo `privado/formacao-complementar/PAINEL_PESSOAL.md` e `PROGRESSO.md` (acompanhamento pessoal fica no Drive; o repositório só tem os módulos) | Nunca misturar com a Univesp |

Material privado correspondente: `privado/estudo/<bimestre>/` (coletas, apostilas com gabarito, roteiro de podcast e os dois geradores que os produzem) e `privado/formacao-complementar/00-fundamentos/` (prova diagnóstica e respostas).

## Regra de revisão para provas Univesp (desde 22/09/2026)

Origem: na prova de 22/09/2026 o guia cobriu só 6 de 19 questões. A coleta do AVA tinha pegado título, "Em síntese" e 300 caracteres de legenda. Ninguém leu os textos-base inteiros, as videoaulas inteiras nem os questionários das atividades avaliativas. Conferido depois no AVA: os temas que faltaram (LLL, "deslize", Geraldi e a "cidade das letras", Orlandi, Geertz e Tylor, a frase dos "botes") estavam todos no material.

Para qualquer guia, apostila ou simulado de prova (próxima rodada: provas regulares do 4º bimestre, 09 a 19/11/2026):

1. **Fonte inteira, não resumo.** Ler por completo: todo PDF de `assets.univesp.br` (textos-base, textos de apoio, **slides das videoaulas**), as páginas Início/Videoaulas/Material-base/Aprofundando/Em síntese e a transcrição completa das videoaulas.
2. **Questionários primeiro.** Baixar a revisão (`review.php`) de todas as atividades avaliativas, com enunciado, alternativas e feedback. A prova sai do mesmo banco e no mesmo formato (asserção-razão, "I, II e III", completar lacunas). **Isso vai para `privado/`, nunca para o repositório.**
3. **Autores e exemplos citados entram no guia**, mesmo que pareçam secundários: todo nome de autor, sigla e exemplo concreto dos slides (ex.: "Não há botes para todos...").
4. **Material externo (LTI/Biblioteca Virtual) que não abrir** fica listado no guia como "não lido", nunca omitido em silêncio.
5. **Proibido escrever "conferido contra o AVA"** sem ter cumprido os itens 1 e 2. Antes de entregar, rodar um checklist: para cada semana, quais PDFs, vídeos e questionários foram lidos.
6. Caminho técnico: `python automacao/ava_vivo.py` sobe o Chrome logado (CDP 9222); de lá, listar `course/view.php` das disciplinas e percorrer todos os módulos.
