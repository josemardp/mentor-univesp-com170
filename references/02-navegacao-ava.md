# Navegação geral do AVA (Moodle Univesp)

> Snapshot de 02/07/2026. URL base: https://ava.univesp.br

## Como logar
- Login: https://ava.univesp.br/my/ redireciona para tela "Bem-vindo(a) de volta!" (e-mail institucional), depois para `login.univesp.br/simplesaml/...` ("#SOU Sistema Operacional Univesp") onde se digita a senha e clica **ENTRAR**.
- A página do AVA (Moodle) faz polling/AJAX contínuo (notificações, mensagens) — pode parecer que "nunca termina de carregar" em ferramentas de automação, mas é normal, a página funciona.

## Menu superior (barra preta, fixo em todas as páginas logadas)
- **Painel** → https://ava.univesp.br/my/ (dashboard/home)
- **Meus cursos**: https://ava.univesp.br/my/courses.php (listagem padrão Moodle) e https://ava.univesp.br/admin/tool/custompage/view.php?id=3 (página customizada Univesp, cards visuais)
- **Manual do Aluno** → https://apps.univesp.br/manual-do-aluno/ (abre em nova aba)
- **Mais** → menu suspenso adicional
- Ícone de sino (notificações) → popup; "Mostrar todos" → https://ava.univesp.br/message/output/popup/notifications.php
- Ícone de balão (mensagens) → painel lateral de chat Moodle; "Mostrar todos" → https://ava.univesp.br/message/index.php
- Avatar do usuário (canto superior direito) → menu suspenso:
  - **Perfil** → https://ava.univesp.br/user/profile.php
  - **Notas** (gerais, todos os cursos) → https://ava.univesp.br/grade/report/overview/index.php
  - **Calendário** → https://ava.univesp.br/calendar/view.php?view=month
  - **Arquivos privados** → https://ava.univesp.br/user/files.php
  - **Relatórios** → https://ava.univesp.br/reportbuilder/index.php
  - **Preferências** → https://ava.univesp.br/user/preferences.php
  - **Sair** (logout) — o link tem um `sesskey` que muda a cada sessão, não dá pra salvar/reusar

## Gaveta lateral esquerda ("Blocos")
- Botão "Abrir gaveta de blocos" abre painel com blocos Moodle. Bloco encontrado: **Exabis ePortfolio** (My CV, My Views, Shared Views/Categories, Import/Export) — portfólio pessoal do aluno, pouco relevante para navegação de disciplina.

## Painel/Dashboard (https://ava.univesp.br/my/) — conteúdo central
A home é composta por blocos informativos (banners), nesta ordem:

1. **Acessibilidade** — Política Geral de Acessibilidade (PDF), SEI (https://sei.univesp.br/), SAE (https://atendimento.univesp.br/sae/alunos_univesp.html).
2. **Aviso "Atenção ao calendário Acadêmico"** — explica que ingressantes de Licenciatura fazem o AIA em LET100, os demais (inclui Josemar) em COM170; atividades abertas só para ingressantes nesse período.
3. **"Escolha seu destino"** — Portal do Aluno (https://sei.univesp.br/, mesmo destino do SEI), Email/Teams/Office 365 (https://login.microsoftonline.com/login.srf?wa=wsignin1.0&whr=aluno.univesp.br), SAE (http://atendimento.univesp.br/sae/portal.html), Carreira Univesp (https://univesp.br/carreiras), Tutoriais (https://apps.univesp.br/tutoriais-univesp/).
4. **"Recursos Didáticos"** — Pearson (SSO), Minha Biblioteca (SSO), Manual do Aluno, Repositório de REAs (https://apps.univesp.br/repositorio/).
5. **"Provas"** — Calendário geral de provas (https://apps.univesp.br/manual-do-aluno/calendario-provas/), vídeos de orientação, Glossário de provas (https://apps.univesp.br/glossario-de-provas/), FAQ Provas em PDF, tutorial para recorrer a uma questão, página sobre uso acadêmico de IA, Questões objetivas.

## Rodapé
- "Contate o suporte do site" → SAE (http://atendimento.univesp.br/sae/portal.html)
- "Ver perfil" → https://ava.univesp.br/user/profile.php?id=134270
- "Resumo de retenção de dados" → https://ava.univesp.br/admin/tool/dataprivacy/summary.php

## Observações importantes
- O painel do Moodle **não lista os cursos matriculados na home** — é preciso ir em "Meus cursos" no menu superior.
- Muitos recursos "oficiais" (Portal do Aluno/SEI, SAE, Biblioteca, Pearson) ficam fora do domínio ava.univesp.br, em subdomínios próprios da Univesp — é normal ser redirecionado para outro site.
