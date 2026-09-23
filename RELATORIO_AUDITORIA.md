# Auditoria do pipeline da apostila de prova

Data: 23/09/2026. Branch: `codex/auditoria-apostila`.

Escopo: coleta e montagem semanal, prompts, HTML/PDF, tarefa agendada e testes. O exemplo do 3º bimestre foi inspecionado apenas em `privado/`. Nenhuma fonte, questão, resposta ou dado pessoal foi copiado para este repositório.

## Achados, em ordem de gravidade

| Gravidade | Local | Problema e impacto | Providência |
|---|---|---|---|
| Alta | `automacao/revisao_semanal.py:613`; `automacao/rodar_diario.ps1:287` | No logon após suspensão, a revisão podia usar `docs/data.json` de outro dia, concluir sem enxergar material novo e receber a marca semanal de feita. Uma falha anterior à escrita do resumo ainda podia notificar o resumo antigo. | Exigir retrato do dia antes da revisão; erro impede a marca. Apagar o resumo antigo antes da chamada. Testes sintéticos de data e ordem da rotina. |
| Alta | `automacao/revisao_semanal.py:319`, `automacao/revisao_semanal.py:342`, `automacao/revisao_semanal.py:370` | Erro do `yt-dlp` virava “sem legenda”; página vazia e revisão de quiz sem `.que` podiam virar “lido”. Isso encerrava semanas com cobertura falsa após falha de rede, sessão ou mudança de layout. | Marcar falha para nova tentativa; testes com retorno de erro e páginas vazias. PDF sem texto extraível passou a “não lido” em `automacao/revisao_semanal.py:304`. |
| Alta | `automacao/revisao_semanal.py:194`, `automacao/revisao_semanal.py:633`, `automacao/revisao_semanal.py:728` | O manifesto bastava para pular revisão ou ficha apagada/corrompida; uma fonte com falha podia terminar com código 0 e receber a marca semanal de feita. | Conferir existência e validade dos produtos, detectar novos itens no inventário da seção e devolver erro quando houver fonte com falha. Testes de retomada e de inventário. |
| Média | `automacao/apostila.py:546` | PDF antigo podia continuar após a remoção de todas as questões; interrupção durante a geração deixava saída parcial. | Gerar HTML e PDFs temporários e só publicar após todos ficarem prontos; remover treino obsoleto. Teste de duas montagens sintéticas. |
| Média | `automacao/apostila.py:178`, `automacao/apostila.py:395` | A ficha e o manifesto repetiam avisos de fontes não lidas, aumentando a primeira semana e empurrando as últimas linhas para outra página. | Usar o manifesto como origem única da cobertura e iniciar cada semana em página nova no resumo. Teste sintético e inspeção visual dos PDFs reais. |
| Média | `automacao/revisao_semanal.py:179`, `automacao/revisao_semanal.py:243`, `automacao/revisao_semanal.py:304`, `automacao/revisao_semanal.py:552` | Fontes de mesmo tamanho não mudavam a assinatura; PDFs homônimos sobrescreviam a extração; uma saída parcial do Claude com código de erro podia ser aceita. | Guardar hash do texto, distinguir PDFs pela URL e exigir saída com código 0. Testes com textos sintéticos. |
| Baixa | `automacao/revisao_semanal_prompt.md:3`; `automacao/apostila_prompt.md:22`; `automacao/apostila.py:65` | O prompt de revisão não priorizava explicitamente os questionários nem todos os PDFs; lacunas podiam sumir da ficha; JSON com coleção em formato errado podia quebrar a montagem. | Ajustar os prompts e normalizar listas inválidas. A cobertura da apostila agora vem do manifesto, inclusive falhas e questionário sem revisão. |

## Verificação

- As 14 suítes `testes/test_*.py` passaram no Git Bash. Os testes novos usam apenas dados sintéticos. A sintaxe de `rodar_diario.ps1` passou pelo parser do PowerShell sem erro.
- `python automacao/apostila.py --bimestre 2026-3bim` terminou sem erro. `pdfinfo` mostrou 2 páginas em cada resumo de 2 semanas, exatamente uma página por semana. Os dois cadernos de treino permaneceram em 3 páginas cada.
- Páginas dos resumos renderizadas e inspecionadas; HTML conferido em viewport de celular. Não houve corte visível de texto ou tabela. A busca, o tema, o progresso e a resposta clicável permanecem no HTML.

## Decisões de não mudar

- Leitores externos protegidos continuam como “não lido”, conforme a regra do projeto e os termos de uso. PDF de imagem sem texto extraível também fica explícito como “não lido”; não foi adicionada OCR.
- A meta de uma página A4 por semana e a separação entre resumo e treino foram preservadas.
- Não houve coleta no AVA, execução de `claude -p`, montagem em lote, alteração em `docs/` ou `.project-mentor/`, nem mudança do Agendador nesta máquina.

## Pendências e riscos

1. `automacao/rodar_diario.ps1:179`: a trava protege somente uma máquina. Duas máquinas podem abrir a mesma sessão do AVA e escrever simultaneamente na pasta sincronizada pelo Drive. Um arquivo de trava no Drive não oferece exclusão distribuída confiável. Definir uma máquina responsável pela revisão ou um coordenador externo antes de agendar em ambas.
2. `automacao/configurar_local.ps1:41` e `automacao/rodar_diario.ps1:208`: “repetir em 3 h” depende de novo gatilho de logon/desbloqueio; não existe gatilho periódico de repetição após limite de uso ou falha. Uma máquina ligada e sem desbloqueio pode esperar até a próxima segunda. Revisar o agendamento com teste local do Agendador.
3. `automacao/revisao_semanal.py:407`: páginas já lidas não são reabertas em toda segunda. O novo inventário detecta itens novos na seção, mas alterações internas em uma página antiga podem passar despercebidas. Definir janela de rechecagem sem multiplicar chamadas ao AVA.
4. `automacao/revisao_semanal.py:342`: o seletor `.que` detecta uma revisão vazia, mas mudanças parciais no HTML do Moodle ainda podem omitir alternativas ou feedback. Validar a primeira rodada real e comparar a `COBERTURA.md` com os arquivos de fontes, sem declarar “conferido contra o AVA” antes do checklist integral da regra.
5. `automacao/apostila.py:65`: os limites de palavras permanecem no prompt; o validador corta quantidade de itens, mas não mede o comprimento de cada frase. Fichas futuras muito longas podem ultrapassar uma página. Conferir `pdfinfo` nas primeiras semanas do 4º bimestre e acrescentar um aviso de paginação se o problema aparecer.
