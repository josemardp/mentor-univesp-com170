# Memória de Contexto - Projeto Mentor Univesp (Josemar)

Este arquivo serve como a **memória de longo prazo** do projeto. Sempre que uma nova sessão for iniciada, leia este arquivo primeiro para entender o contexto, as credenciais, o status atual e os próximos passos.

## 1. Informações Pessoais e Acesso
- **Aluno:** Josemar de Paula
- **Credenciais do AVA:** NÃO ficam aqui. Este repositório é **público**. Usuário
  e senha vivem só nos Secrets do GitHub (`AVA_USUARIO`, `AVA_SENHA`), usados
  pela Action. Nunca escreva senha em arquivo versionado.
- **Curso:** Bacharelado em Inteligência Artificial (BIA)
- **Turma:** 001
- **Semestre:** 2026/2

## 2. Disciplinas Atuais (Módulos Abertos)
Atualmente, o aluno está cursando as seguintes disciplinas (baseado no `docs/data.json`):
1. **COM100** - Pensamento Computacional
2. **SOC100** - Ética, cidadania e Sociedade
3. **LET110** - Leitura e Produção de textos
4. **COM170** - Inteligência Artificial na Prática Acadêmica e Profissional

## 3. Histórico de Ações e Tarefas Concluídas

### Sessão 30/07/2026 - Resposta aos Fóruns COM100
- **Contexto:** O aluno pediu para assumir o controle do AVA e responder aos fóruns pendentes onde ainda não havia postado nada.
- **Disciplina:** COM100 - Pensamento Computacional
- **Módulos Abertos:** Semana 1 e Semana 2
- **Ações Realizadas:**
  1. **S2 - Fórum temático:** Postado com sucesso (Post #536931).
     - *Tema:* Os quatro pilares do pensamento computacional na prática.
     - *Conteúdo:* O aluno escolheu "lavar louça" como atividade cotidiana e detalhou os 4 pilares (Abstração, Decomposição, Reconhecimento de Padrões e Algoritmos) aplicados à tarefa.
  2. **S2 - Fórum de dúvidas gerais:** Postado com sucesso (Post #536940).
     - *Tema:* Discussões sobre o conteúdo das semanas.
     - *Conteúdo:* Comentou sobre os 4 pilares e tirou uma dúvida sobre quando começariam as lives (terceira semana) e se a atividade avaliativa da Semana 2 cobraria o conteúdo da Semana 1.
- **Observação Importante:** O fórum S1 - Fórum de dúvidas gerais já possuía um post anterior do aluno ("Boa noite"), por isso foi mantido e não foi postado novamente, conforme solicitação.

### Sessão 08/09/2026 - colega e Ponto de encontro COM170 (Quinzena 4)
- **Contexto:** Josemar recebeu de colegas (dois colegas) PDFs com o Portfólio
  Individual deles do COM170, Quinzena 4 Módulo 6, e pediu ajuda pra entender e
  fazer o próprio, que estava com o Caso B ("O resumo sem a segunda aba").
- **Ações realizadas:**
  1. Conferido ao vivo no AVA: Q4 M6 (colega, prazo 12/09 23:59) e
     Q4 M7 (fórum "Ponto de encontro" + Laboratório "Trabalho em grupo",
     mesmo prazo) ainda pendentes.
  2. Montada a Parte 1 do portfólio usando um exemplo real (consulta à apólice
     de seguro Porto via skill `seguro-porto`, cobertura de carro reserva) e a
     Parte 2 com o Caso B oficial (baixado de
     `assets.univesp.br/.../Q4_M5_CASO_B.pdf`).
  3. PDF gerado e **enviado no Laboratório de Revisão do Módulo 6** (envio
     confirmado no AVA, 08/09 13:51, arquivo `Portfolio_Individual_Q4_M6.pdf`).
  4. Postado no fórum "Q4 M7 - Ponto de encontro" (tópico do colega, grupo G4):
     resumo do Caso B + comparação com o Caso A dele.
  5. Postada pergunta no mesmo fórum sobre quem é o representante da quinzena
     (ninguém confirmado ainda; Josemar foi representante na Q1, não nas Q2/Q3).
  6. Comparados os PDFs dos colegas com os casos oficiais (Q4_M5_CASO_A/B/C):
     conteúdo bate (mesmo universo "Nexo", casos A/B/C corretos), mas o
     documento da colega usa framework de outra versão/quinzena (ex.: Fecho dela
     é "O que levo para o grupo" em vez das 3 linhas oficiais "O que faltou /
     Quando poderia ter sido evitado / A providência" — não serve direto pro
     Bloco 1 do Protocolo em grupo sem ajuste).
- **Observação:** nenhuma mudança de código nesta sessão, só uso do
  robô/skills para apoiar o aluno. `.playwright-mcp/` (usado pra upload no
  AVA) é ignorado pelo git, não sobrou nada solto no repo.

## 4. Aprendizados e Preferências do Usuário
- O usuário prefere que os commits sejam feitos diretamente na branch principal (`main`), sem a criação de branches intermediárias.
- O usuário gosta de um estilo "padrão dos estudantes" para respostas em fóruns (não muito formal, mas acadêmico e engajado).
- O usuário valoriza o aprendizado constante: a cada novo aprendizado, o sistema deve incorporar as informações, fazer commit e push na main.

## 5. Próximos Passos Imediatos
- [ ] **Trocar a senha do AVA.** Ela ficou em texto puro neste arquivo, num
      repositório público, entre 30/07 e 04/08/2026. Foi removida do arquivo em
      04/08, mas continua no histórico do Git: só a troca resolve.
- [ ] Monitorar o AVA para novas liberações de módulos ou prazos de atividades.
- [ ] **COM170 Q4 M7:** grupo G4 ainda não decidiu quem é o representante da
      quinzena (pergunta postada no fórum em 08/09, sem resposta ainda).
      Prazo do Protocolo em grupo: sábado 12/09, 23:59.
- [ ] **COM170 Q4 M7:** avisar a colega (fora do AVA, zap do grupo) que o Fecho
      dela está num formato diferente do que o Bloco 1 do Protocolo precisa.

---
*Última atualização: 08/09/2026*
