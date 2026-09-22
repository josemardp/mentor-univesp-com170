#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Controle de Assimilação de Conhecimento — Rastreamento Ativo (Univesp e Formação)
Permite visualizar prontidão de prova, registrar desempenho em simulados e marcar assimilação.
"""

import os
import sys
import json
import argparse
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JSON_PATH = os.path.join(BASE_DIR, "2026-3bim", "matriz_dados.json")
MD_PATH = os.path.join(BASE_DIR, "2026-3bim", "MATRIZ_ASSIMILACAO.md")

STATUS_ICONS = {
    "pendente": "⚪",
    "estudo": "🟡",
    "assimilado": "🔵",
    "internalizado": "🟢",
    "revisar": "🔴"
}

STATUS_LABELS = {
    "pendente": "Pendente",
    "estudo": "Em Estudo",
    "assimilado": "Assimilado",
    "internalizado": "Internalizado",
    "revisar": "Revisar Urgente"
}

PESOS = {
    "internalizado": 1.0,
    "assimilado": 0.70,
    "estudo": 0.25,
    "pendente": 0.0,
    "revisar": 0.10
}

def carregar_dados():
    if not os.path.exists(JSON_PATH):
        print(f"Erro: arquivo de dados não encontrado em {JSON_PATH}")
        sys.exit(1)
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_dados(dados):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def barra_progresso(percentual, largura=24):
    preenchido = int(round(largura * percentual / 100))
    barra = "█" * preenchido + "░" * (largura - preenchido)
    return f"[{barra}] {percentual:5.1f}%"

def calcular_metricas(topicos):
    disciplinas = {}
    for t in topicos:
        disc = t["disciplina"]
        if disc not in disciplinas:
            disciplinas[disc] = {
                "nome": t["disciplina_nome"],
                "total": 0,
                "internalizado": 0,
                "assimilado": 0,
                "estudo": 0,
                "pendente": 0,
                "revisar": 0,
                "pontos": 0.0
            }
        st = t.get("status", "pendente").lower()
        if st not in PESOS:
            st = "pendente"
        disciplinas[disc]["total"] += 1
        disciplinas[disc][st] = disciplinas[disc].get(st, 0) + 1
        disciplinas[disc]["pontos"] += PESOS.get(st, 0.0)

    for disc, dados in disciplinas.items():
        if dados["total"] > 0:
            dados["ipp"] = (dados["pontos"] / dados["total"]) * 100.0
        else:
            dados["ipp"] = 0.0

    total_geral = len(topicos)
    pontos_geral = sum(PESOS.get(t.get("status", "pendente").lower(), 0.0) for t in topicos)
    ipp_geral = (pontos_geral / total_geral * 100.0) if total_geral > 0 else 0.0

    return {
        "disciplinas": disciplinas,
        "total": total_geral,
        "ipp_geral": ipp_geral,
        "internalizado": sum(1 for t in topicos if t.get("status") == "internalizado"),
        "assimilado": sum(1 for t in topicos if t.get("status") == "assimilado"),
        "estudo": sum(1 for t in topicos if t.get("status") == "estudo"),
        "pendente": sum(1 for t in topicos if t.get("status") == "pendente"),
        "revisar": sum(1 for t in topicos if t.get("status") == "revisar"),
    }

def gerar_markdown(dados):
    metricas = calcular_metricas(dados["topicos"])
    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")

    md = []
    md.append("# Matriz e Controle de Assimilação de Conhecimentos — Provas Univesp")
    md.append("")
    md.append(f"> **Meta:** Provas Presenciais em **22/09/2026** (COM100, SOC100, LET110)")
    md.append(f"> **Última sincronização:** {hoje} · **Total de tópicos mapeados:** {metricas['total']}")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 1. Painel de Prontidão da Prova (IPP)")
    md.append("")
    md.append("O **IPP (Índice de Prontidão de Prova)** mede o domínio real baseado em retenção ativa:")
    md.append("`IPP = (1.0 × Internalizados + 0.7 × Assimilados + 0.25 × Em Estudo) / Total`")
    md.append("")
    md.append(f"**Prontidão Geral:** `{barra_progresso(metricas['ipp_geral'])}`")
    md.append("")
    md.append("| Disciplina | Nome | Tópicos | Internalizados | Assimilados | Em Estudo | Pendentes | Revisar | IPP (%) |")
    md.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")

    for disc, d in metricas["disciplinas"].items():
        md.append(f"| **{disc}** | {d['nome']} | {d['total']} | 🟢 {d['internalizado']} | 🔵 {d['assimilado']} | 🟡 {d['estudo']} | ⚪ {d['pendente']} | 🔴 {d['revisar']} | `{barra_progresso(d['ipp'], largura=12)}` |")

    md.append("")
    md.append("### Legenda dos Níveis de Assimilação:")
    md.append("- `⚪ PENDENTE` (Nível 0): Conteúdo não visto ou simulado não iniciado.")
    md.append("- `🟡 EM ESTUDO` (Nível 1): Apostila lida e conceitos mapeados (ainda sem validação de retenção em questões).")
    md.append("- `🔵 ASSIMILADO` (Nível 2): Acertou as questões no simulado (≥ 70%) e compreendeu a justificativa da banca.")
    md.append("- `🟢 INTERNALIZADO` (Nível 3): Domínio pleno. Lembra do conceito sem consulta, explica com as próprias palavras e superou as pegadinhas.")
    md.append("- `🔴 REVISAR URGENTE`: Errou questão recente de simulado ou apresentou dúvida conceitual crítica.")
    md.append("")
    md.append("---")
    md.append("")

    # Tabela por disciplina
    disciplinas_ordenadas = ["COM100", "SOC100", "LET110"]
    for disc in disciplinas_ordenadas:
        topicos_disc = [t for t in dados["topicos"] if t["disciplina"] == disc]
        if not topicos_disc:
            continue
        nome_disc = topicos_disc[0]["disciplina_nome"]
        md.append(f"## 2. {disc} — {nome_disc}")
        md.append("")
        md.append("| ID | Sem. | Tópico Principal | Conceitos-Chave da Banca | Status | Acertos | Última Rev. | Autoexplicação / Síntese |")
        md.append("| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |")
        for t in topicos_disc:
            icon = STATUS_ICONS.get(t.get("status", "pendente"), "⚪")
            st_label = STATUS_LABELS.get(t.get("status", "pendente"), "Pendente")
            acertos = t.get("acertos", "0/0")
            rev = t.get("data_revisao", "-")
            auto = t.get("autoexplicacao", "").strip()
            if not auto:
                auto = "-"
            md.append(f"| `{t['id']}` | S{t['semana']:02d} | **{t['titulo']}** | {t['conceitos_chave']} | {icon} {st_label} | `{acertos}` | {rev} | {auto} |")
        md.append("")

    md.append("---")
    md.append("")
    md.append("## 3. Como usar e atualizar")
    md.append("")
    md.append("### No Chat com o Tutor (Antigravity):")
    md.append("- Quando você responde as questões de simulado aqui, o tutor atualiza automaticamente o status (`⚪` ➔ `🔵` ➔ `🟢`).")
    md.append("")
    md.append("### No Terminal (CLI):")
    md.append("```powershell")
    md.append("# Visualizar painel resumido de prontidão:")
    md.append("python estudo/ferramentas/assimilar.py status")
    md.append("")
    md.append("# Marcar um tópico como assimilado ou internalizado:")
    md.append('python estudo/ferramentas/assimilar.py marcar COM-01 --status internalizado --acertos "4/4" --explicacao "Domino os 4 pilares e os 3 eixos BNCC"')
    md.append("")
    md.append("# Marcar tópico para revisão imediata (errou questão):")
    md.append('python estudo/ferramentas/assimilar.py marcar SOC-02 --status revisar --acertos "1/3" --obs "Confundi imperativo categorico com utilitarismo"')
    md.append("")
    md.append("# Sincronizar o arquivo markdown após edições no JSON:")
    md.append("python estudo/ferramentas/assimilar.py sync")
    md.append("```")
    md.append("")

    return "\n".join(md)

def cmd_status(dados):
    metricas = calcular_metricas(dados["topicos"])
    print("\n" + "=" * 68)
    print(" 📊 PAINEL DE CONTROLE DE ASSIMILAÇÃO — PROVAS UNIVESP 22/09/2026")
    print("=" * 68)
    print(f"\n Prontidão Geral: {barra_progresso(metricas['ipp_geral'], largura=26)}")
    print(f" Status dos 24 tópicos: 🟢 {metricas['internalizado']} internalizados | 🔵 {metricas['assimilado']} assimilados | 🟡 {metricas['estudo']} em estudo | ⚪ {metricas['pendente']} pendentes | 🔴 {metricas['revisar']} a revisar")
    print("\n" + "-" * 68)
    print(f" {'DISCIPLINA':<9} | {'NOME':<28} | {'IPP':<17} | {'CONCLUÍDOS':<10}")
    print("-" * 68)
    for disc, d in metricas["disciplinas"].items():
        prog = barra_progresso(d["ipp"], largura=10)
        conc = f"{d['internalizado'] + d['assimilado']}/{d['total']}"
        print(f" {disc:<9} | {d['nome']:<28} | {prog:<17} | {conc:<10}")
    print("-" * 68)

    revisar_lista = [t for t in dados["topicos"] if t.get("status") == "revisar"]
    if revisar_lista:
        print("\n ⚠️  ATENÇÃO — TÓPICOS MARCADOS PARA REVISÃO IMEDIATA:")
        for t in revisar_lista:
            print(f"   • [{t['id']}] {t['disciplina']} - {t['titulo']} (Obs: {t.get('obs', 'Sem detalhes')})")
    else:
        print("\n ✨ Nenhum tópico crítico em alerta de revisão no momento.")
    print("\n Dica: rode 'python estudo/ferramentas/assimilar.py sync' para atualizar o Markdown.\n")

def cmd_marcar(dados, args):
    topico_id = args.id.upper()
    topico = next((t for t in dados["topicos"] if t["id"].upper() == topico_id), None)
    if not topico:
        print(f"Erro: tópico '{topico_id}' não encontrado!")
        sys.exit(1)

    if args.status:
        st = args.status.lower()
        if st not in STATUS_LABELS:
            print(f"Erro: status inválido '{args.status}'. Opções: {list(STATUS_LABELS.keys())}")
            sys.exit(1)
        topico["status"] = st

    if args.acertos:
        topico["acertos"] = args.acertos

    if args.explicacao:
        topico["autoexplicacao"] = args.explicacao

    if args.obs:
        topico["obs"] = args.obs

    topico["data_revisao"] = datetime.now().strftime("%d/%m")

    dados["ultima_atualizacao"] = datetime.now().strftime("%Y-%m-%d")
    salvar_dados(dados)

    md_content = gerar_markdown(dados)
    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)

    icon = STATUS_ICONS.get(topico["status"], "⚪")
    print(f"\n✅ Tópico [{topico['id']}] atualizado com sucesso!")
    print(f"   Status: {icon} {STATUS_LABELS[topico['status']]}")
    print(f"   Acertos: {topico.get('acertos', '-')}")
    print(f"   Última Revisão: {topico['data_revisao']}")
    if topico.get("autoexplicacao"):
        print(f"   Síntese: {topico['autoexplicacao']}")
    print(f"   Markdown sincronizado em: {MD_PATH}\n")

def cmd_sync(dados):
    md_content = gerar_markdown(dados)
    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"\n✅ {MD_PATH} sincronizado com sucesso a partir dos dados estruturados!\n")

def main():
    parser = argparse.ArgumentParser(description="Controle de Assimilação de Conhecimentos (Univesp e Formação)")
    subparsers = parser.add_subparsers(dest="comando")

    # Comando status
    subparsers.add_parser("status", help="Exibe o painel de prontidão e métricas")

    # Comando sync
    subparsers.add_parser("sync", help="Regera o arquivo MATRIZ_ASSIMILACAO.md")

    # Comando marcar
    p_marcar = subparsers.add_parser("marcar", help="Atualiza status de um tópico")
    p_marcar.add_argument("id", help="ID do tópico (ex: COM-01, SOC-02, LET-05)")
    p_marcar.add_argument("--status", choices=list(STATUS_LABELS.keys()), required=True, help="Nível de assimilação")
    p_marcar.add_argument("--acertos", help="Desempenho em questões (ex: 4/4 ou 2/3)")
    p_marcar.add_argument("--explicacao", help="Breve síntese ou autoexplicação do conceito")
    p_marcar.add_argument("--obs", help="Observações sobre dúvidas ou pegadinhas")

    args = parser.parse_args()
    dados = carregar_dados()

    if args.comando == "status" or args.comando is None:
        cmd_status(dados)
    elif args.comando == "sync":
        cmd_sync(dados)
    elif args.comando == "marcar":
        cmd_marcar(dados, args)

if __name__ == "__main__":
    main()
