# mentor-univesp

Agente que acompanha um curso universitário a distância no lugar do aluno: entra no
ambiente virtual (Moodle) e nos sistemas satélite, lê o que mudou, cruza prazos, fóruns,
notas e avisos, e entrega um briefing diário do que precisa ser feito.

Construído para uso real, todo dia, num curso em andamento. Roda sozinho cinco vezes ao
dia no GitHub Actions e envia o resumo por e-mail de manhã.

## O que este repositório demonstra

- **Automação de navegador contra sistemas que não têm API.** Playwright em Python
  operando Moodle, portal do aluno e Outlook institucional, com login via SSO federado
  (Microsoft, cache MSAL) e tratamento explícito das telas que quebram o fluxo
  (verificação anti-robô, sessão expirada, tenant que bloqueia autorregistro).
- **Arquitetura de fontes isoladas.** Cada sistema é uma fonte independente em
  `automacao/fontes/`: boletim, calendário, cronograma, disciplinas, fóruns, itens,
  posts próprios, Outlook, portal. Uma fonte que falha não derruba as outras; o
  resultado sai marcado como `falhou` ou `não aplicável`, nunca como dado inventado.
  Há teste específico para isso (`test_isolamento_fontes.py`).
- **Testes onde o risco mora.** Doze suítes em `testes/`, incluindo um *golden test*
  que compara a saída contra um snapshot sanitizado, testes de parsing de prazos,
  de participação em fórum, de revisão entre pares e de login. Rodam antes de cada
  execução agendada; se falham, a rodada não publica.
- **Operação documentada como engenharia.** `STATUS.md` registra o estado real do
  sistema, sessão a sessão. Cinco rodadas de auditoria independente estão
  versionadas na raiz, com achados e correções. Decisões que não são óbvias no
  código estão escritas, com data e motivo.
- **Credenciais fora do repositório, sempre.** Senha, sessão salva e SMTP vivem em
  GitHub Secrets. O script que as cadastra (`automacao/salvar_credenciais.py`) lê
  a senha sem eco e não grava em arquivo. Nunca houve segredo commitado.

## O que este repositório NÃO contém, e por quê

Este é o código que gera o painel. O painel e os dados que ele consome ficam **fora
do controle de versão**, por regra:

- `docs/estado.json` e `docs/data.json` guardam posts de fórum, com nome completo dos
  colegas, raspados de ambiente que exige login. Isso é dado pessoal de terceiro e
  **não entra em repositório**, muito menos público.
- `docs/index.html` é o briefing do aluno, com notas e desempenho. Dado pessoal.

Os três estão no `.gitignore`. O `git add` deles não passa, nem pelo workflow. Quem
clonar e rodar o gerador produz os próprios arquivos localmente, e eles ficam só ali.

Essa regra foi escrita em setembro de 2026, depois de uma auditoria que encontrou o
`estado.json` publicado por engano. A correção não foi só apagar: foi separar o que é
código do que é dado, para que o repositório pudesse ser público sem expor ninguém.

## Como rodar

```bash
pip install -r automacao/requirements.txt
python -m playwright install chromium
python automacao/salvar_credenciais.py     # cadastra AVA_USUARIO e AVA_SENHA nos Secrets
python testes/test_golden.py               # confere que o motor está íntegro
```

A execução agendada está em `.github/workflows/guia-diario.yml`. Para rodar uma vez na
mão, dispare o workflow manualmente ou execute o gerador local.

## Estrutura

```
automacao/         motor: navegação, fontes, geração do painel e do e-mail
automacao/fontes/  uma fonte por sistema, isoladas entre si
testes/            doze suítes; fixtures sanitizadas em testes/fixtures/
references/        notas sobre o curso: calendário, avaliação, navegação
STATUS.md          estado real do sistema, sessão a sessão
AUDITORIA-*.md     cinco rodadas de auditoria independente, com achados e correções
```
