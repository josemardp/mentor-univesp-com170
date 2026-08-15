# Portal do aluno (SEI) — o outro sistema da Univesp

Levantado ao vivo em **15/08/2026**, com a sessão do Josemar. É um retrato, não uma
ligação ao vivo: prazo, nota e recado mudam. Para qualquer coisa que decide ação, abrir
e olhar.

## Por que ele importa

O AVA (`ava.univesp.br`, Moodle) é onde a aula acontece. O portal (`sei.univesp.br`) é
onde a Univesp trata **matrícula, prova, nota oficial, documento e secretaria**. São
sistemas diferentes, com logins diferentes, e há informação que só existe em um deles.

Três coisas ficam invisíveis para quem só olha o AVA:

1. **A data da prova presencial** (só no Sistema de Provas, e é individual).
2. **A lista real de disciplinas matriculadas** (o portal listava 6 em 15/08; o AVA, 4).
3. **Recados da secretaria**, que trazem prazo próprio e não passam por fórum nenhum.

## Login

Duas entradas na tela de acesso (`sei.univesp.br/index.xhtml`):

- **E-mail institucional** → SSO da Microsoft, com MFA. Não automatizável por conta
  própria.
- **Usuário e senha** (campos `form:usuario` e `form:senha`) → aceita as **mesmas
  credenciais do AVA**. É por aqui que o robô entra.

A sessão dura **44 minutos** e é independente da do AVA: estar logado num não loga no
outro. É por isso que ele "precisa logar de novo", e não é erro.

## Mapa das telas (URLs diretas, com a sessão aberta)

| Tela | URL | O que tem |
|---|---|---|
| Tela inicial | `/visaoAluno/telaInicialVisaoAluno.xhtml` | disciplinas matriculadas, integralização curricular, TCC, links úteis, contador de recados não lidos |
| Recados | `/visaoAluno/recadoAluno.xhtml` | caixa de entrada e saída da secretaria |
| Minhas Notas | `/visaoAluno/minhasNotasAlunos.xhtml` | boletim oficial: ATIVIDADE AVA, PROVA, MÉDIA PARCIAL, EXAME, frequência e situação |
| Minhas Disciplinas | `/visaoAluno/minhasDisciplinasAluno.xhtml` | matriz por semestre, carga horária, situação |
| Secretaria On-line | `/visaoAluno/requerimentoAluno.xhtml` | requerimentos (atestado, histórico, tempo estendido, guarda religiosa, revisão de prova) |
| Atividade Complementar | `/visaoAluno/atividadeComplementarAluno.xhtml` | horas extracurriculares e as regras de certificação |
| Documentação Matrícula | `/visaoAluno/entregaDocumentoAluno.xhtml` | documentos entregues e o que falta |
| Documentos Digitais | `/visaoAluno/documentosDigitaisCons.xhtml` | documentos emitidos |

A navegação dentro do portal é JSF/RichFaces: quase todo link tem `href="#"` e roda por
postback. Para automação, ou se usa a URL direta da tabela acima, ou se clica no item de
menu pelo texto.

## Sistema de Provas — o caminho não é uma URL

`Links Úteis → Sistema de Provas`. Chamar `sei.univesp.br/MestreGRSV` direto responde
**404**. A sequência real é:

1. Clicar no botão na tela inicial. Ele dispara `RichFaces.ajax(...)` que **prepara um
   token na sessão** e chama `window.open('../MestreGRSV')`.
2. `GET /MestreGRSV` devolve um HTML com um formulário que se posta sozinho em
   `https://prova.univesp.br/ws/sso/` (campos `login`, `key`, `token`, `headerBar`).
3. Cai em `prova.univesp.br/runner.php?m=13&it=-1&ptp=<base64>`.

Dentro do runner, o `ptp` é base64 simples:

- `src=99992` → Calendário de Atividades
- `tp=HOJE;src=99992` → Atividades disponíveis agora
- `src=99992;p1=09;p2=2026` → calendário de setembro/2026

O bloco **"Suas atividades"** é o que responde a pergunta que importa. Formato:

```
Presencial
2026 - COM100 - PENSAMENTO COMPUTACIONAL - 3 BIMESTRE
De: 05/11 19:40
Até 05/11 23:50
```

O ano só aparece no título; a linha `De:` traz só dia e mês.

## O que estava valendo em 15/08/2026

- **Ciclo de provas do 3º bimestre: 14 a 25 de setembro, 18h às 22h, presencial no
  polo.** É a janela geral, anunciada por recado.
- **A data dele: 05/11, das 19:40 às 23:50**, com **três provas no mesmo dia**: COM100,
  LET110 e SOC100. COM170 não constava no Calendário de Atividades, apesar de a
  disciplina anunciar 60% da nota em prova presencial. Vale perguntar.
- **Seis disciplinas matriculadas**: COM170, LET110, COM100, SOC100, **MMB002
  (Matemática Básica, 80h)** e **INT100 (Projetos e métodos, 40h)**. As duas últimas não
  têm turma aberta no AVA; as turmas que aparecem na busca do Moodle são do bimestre
  anterior (categoria 2026S1B2).
- **Boletim oficial em branco**: todas as parcelas com `--`. As notas do AVA ainda não
  tinham sido consolidadas ali.
- **Documentos de matrícula**: sete tipos entregues em 04/06/2026, com deferimento
  registrado nos recados.
- **Atividade complementar**: nenhum registro. O curso vai exigir horas.

## Regra que não se quebra: o robô não escreve aqui

Medido em 15/08: **abrir `recadoAluno.xhtml` marca sozinho o recado mais recente como
lido** (o contador caiu de 9 para 7 durante a exploração). Por isso a automação nunca
entra na caixa de recados. Ela lê o contador na tela inicial e manda o Josemar abrir.

Aviso consumido pelo robô antes de o dono ver é pior que aviso nenhum. Vale para
qualquer tela do portal com botão que altere estado: requerimento, gravar documento,
alterar cadastro. Leitura sim, escrita nunca.
