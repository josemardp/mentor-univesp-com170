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
