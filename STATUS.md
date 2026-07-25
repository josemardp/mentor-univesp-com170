# STATUS — Guia diário do AVA (mentor-univesp)

> Doc de handoff. Qualquer máquina ou agente retoma a partir daqui.
> Site: https://esdraaline.github.io/mentor-univesp-com170/ (conta GitHub `esdraaline`)

## Última sessão: 25/07/2026

Reestruturação completa da automação. O guia antigo cobrava tarefa que já tinha
fechado, não avisou da live de 23/07 e inventava prazo ("semana = 7 dias" fixo
no código). Foi reescrito de ponta a ponta.

- `coletar.py` (novo): descobre as disciplinas sozinho em "Meus cursos", lê a
  página de cada curso pelo DOM do Moodle, o cronograma oficial da Univesp, o
  calendário, todos os fóruns (incremental), notificações e mensagens.
- `render.py` (novo): site abre com a agenda no imperativo, em ordem de urgência.
- `sessao.py` (novo): login automático no AVA, sem renovação manual.
- `enviar_email.py` (novo): resumo diário por e-mail junto com a atualização.
- `gerar_guia.py`: virou wrapper fino, mantém `--render-only` e o `.bat` antigos.

Quatro bugs achados e corrigidos com o robô já rodando de verdade:

1. Data de abertura virava prazo ("Módulo 6 vence 27/07" quando 27/07 era o dia
   em que ele abria). Agora cada data lida de aviso é classificada início/fim.
2. Aviso de fórum sumia no dia seguinte, levando junto o prazo extraído dele.
   Agora os avisos ficam em cache por 45 dias; o selo "novo" dura 3 dias.
3. Calendário voltava vazio: eu pedia 200 eventos e o Moodle recusa acima de 50.
4. Login falhava: a Univesp usa duas telas (e-mail no AVA → SSO SAML em
   login.univesp.br), não o formulário padrão do Moodle.

## Estado atual

Funcionando e verificado rodando na nuvem. O robô roda todo dia às 8h, entra no
AVA sozinho, lê as 6 fontes, monta a agenda e manda o resumo por e-mail.

Prazos vêm de três fontes, e **a origem de cada data aparece no site**: calendário
do AVA, cronograma oficial e avisos de facilitador (com link pro post). Nenhuma
data é estimada: sem fonte oficial, o site diz que não há prazo.

Secrets configurados no repo `esdraaline/mentor-univesp-com170`: `AVA_USUARIO`,
`AVA_SENHA`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_PARA`.
Nenhuma credencial no repositório (ele é público).

## Próximo passo

- Conferir se a execução automática das 8h roda limpa. Todas as execuções de
  25/07 foram disparadas à mão (`workflow_dispatch`); o caminho do agendador
  ainda não foi exercitado com o código novo.

## Pendências

- **Josemar (estudo):** quiz "Identifique o paradigma" do Módulo 1 do COM170.
  É ele que destrava o Módulo 4, que vence 26/07 às 23:59.
- **Josemar (limpeza):** o Secret `AVA_STORAGE_STATE` ficou obsoleto (era o
  cookie de sessão do sistema antigo). Pode apagar sem risco.
- Revisão semanal da mentora continua manual: escrever `docs/revisao.json` e
  rodar `python automacao/gerar_guia.py --render-only`.
- 19 itens caem em "sem prazo definido". Ainda não é ruído, mas se crescer vale
  agrupar por disciplina ou recolher.
- As sub-seções do AIA no COM170 não são lidas (ficam atrás de uma página
  separada). Sem impacto: o AIA encerrou em 20/07.

## Decisões que valem lembrar

- **Prazo nunca é estimado.** Foi o erro original e não deve voltar.
- **Item fechado sai da fila** e vai pro bloco recolhido "já encerrou".
- **Seção bloqueada com prazo vira alerta**, senão o item mais urgente ficaria
  invisível justo por estar travado.
- **A urgência sobe pela cadeia de módulos:** o que destrava a etapa com prazo
  herda o prazo dela.
- **O site é público**, então mensagem privada entra só como metadado (sem
  conteúdo) e post de fórum entra truncado, com link pro original.
