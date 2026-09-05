# -*- coding: utf-8 -*-
"""
DESATIVADO em 05-06/09/2026 — o robô não lê mais o Outlook institucional.
`pipeline.py` não chama `fontes/outlook_univesp.py`, e o Secret
OUTLOOK_STORAGE_STATE saiu do workflow. Não é bug: o Entra ID limita a sessão
desse tipo de app a 24h sem exceção (não configurável), e a alternativa via
Microsoft Graph (app próprio, refresh token de 90 dias) foi testada e morreu
no bloqueio de autorregistro do tenant da Univesp (401 em entra.microsoft.com
e portal.azure.com). Ver STATUS.md, entrada de 05-06/09/2026, para o
histórico completo. Este script fica no repositório só para o caso de a
política do tenant mudar um dia — rodá-lo hoje grava um Secret que ninguém lê.

Sessão do Outlook institucional pro robô, feita uma vez, com você aprovando
o MFA no celular.

Por que existe: o Outlook (conta-academica@exemplo.edu.br) federa pro mesmo SSO
do AVA, mas passa pelo Microsoft Entra ID antes, e essa conta tem aprovação
por push do Authenticator configurada ali — a cada sessão nova, não só na
primeira vez. O AVA e o Portal do aluno nunca passam pelo Entra ID e nunca
pedem isso; o Outlook pede sempre. O robô roda sozinho na nuvem, cinco vezes
por dia, sem ninguém com o celular na mão pra aprovar.

A saída é a mesma que este projeto já usa pro Sistema de Provas, que fica
atrás de verificação anti-robô: não contornar, e sim guardar uma sessão já
aprovada por você, uma vez, pro robô reaproveitar. Quando vencer, a fonte
"outlook" do guia diz isso sozinha (fica em "falhou", com a mensagem pedindo
pra rodar este script de novo), e o resto do guia continua normal, do jeito
que já continua sem o Portal quando ele cai.

ATENÇÃO, e isto muda o que dá pra esperar deste script: até 05/09/2026 este
texto prometia que a sessão duraria "semanas, não um dia". Está errado, e
nunca foi alcançável. O Outlook web é um app MSAL de página única, e o
Microsoft Entra ID dá a esse tipo de app um refresh token de NO MÁXIMO 24
horas, que não se configura e que renovar não estende (os tokens seguintes
herdam o mesmo vencimento). Passadas as 24h, só um login interativo em
janela de primeiro plano recupera — exatamente o que uma Action agendada não
pode fazer. Medido duas vezes neste projeto: a captura de 29/08 leu bem por
~24h, a de 31/08 por ~12h, e as duas morreram em seguida.

Ou seja: rodar este script compra menos de um dia de leitura, não semanas.
Enquanto a decisão de fundo não for tomada (encaminhar o e-mail
institucional pro Gmail, ou tirar esta fonte do robô), esta é a expectativa
correta. Ver STATUS.md, entrada de 05/09/2026.

O que este script faz:
  1. Abre um Chrome VISÍVEL — você precisa ver a tela pra aprovar o MFA.
  2. Você faz o login à mão: aprova no Authenticator e clica em
     "Sim" / "Manter-me conectado" quando a Microsoft perguntar. (Esse
     "sim" ajuda o login seguinte, mas não estica o teto de 24h acima.)
  3. Assim que a caixa de entrada aparecer na tela, aperte ENTER aqui no
     terminal. O script confere que saiu da tela de login antes de salvar.
  4. A sessão (cookies + cache de autenticação do MSAL, nunca a senha) vai
     direto pro cofre de Secrets do GitHub, como OUTLOOK_STORAGE_STATE. Não
     fica gravada em arquivo nenhum deste computador.

Rode com:  python automacao/capturar_sessao_outlook.py
"""
import json
import subprocess
import sys

from playwright.sync_api import sync_playwright

REPO = "esdraaline/mentor-univesp-com170"
MAIL_URL = "https://outlook.office.com/mail/"
DOMINIOS_DE_LOGIN = (
    "login.microsoftonline.com",
    "login.univesp.br",
    "login.live.com",
)


def gh_ok():
    try:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def gravar(nome, valor):
    """Manda pro GitHub via stdin, pro valor não aparecer na linha de comando."""
    r = subprocess.run(
        ["gh", "secret", "set", nome, "--repo", REPO],
        input=valor, text=True, capture_output=True,
    )
    if r.returncode != 0:
        # a saída do gh não contém o valor, só o nome do segredo
        print(f"  falhou ao gravar {nome}: {r.stderr.strip()[:300]}")
        return False
    print(f"  {nome} guardado no cofre.")
    return True


def main():
    print("\n=== Sessão do Outlook institucional ===\n")
    if not gh_ok():
        print("O GitHub CLI não está conectado nesta máquina.")
        print("Abra o terminal, rode 'gh auth login', e depois tente de novo.")
        return 1

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=False)
        contexto = navegador.new_context()
        page = contexto.new_page()
        try:
            page.goto(MAIL_URL, wait_until="domcontentloaded", timeout=45000)
        except Exception as erro:
            print(f"Não consegui abrir o Outlook ({type(erro).__name__}).")
            navegador.close()
            return 1

        print("Uma janela do Chrome abriu. Faça o login com a conta")
        print("conta-academica@exemplo.edu.br: aprove o pedido no Authenticator e")
        print('clique em "Sim" quando ele perguntar se quer continuar')
        print("conectado. Deixe a janela aberta até a caixa de e-mail aparecer.\n")
        input("Pressione ENTER aqui quando a caixa de e-mail estiver na tela... ")

        pronto = False
        for _ in range(5):
            url = page.url or ""
            if not any(dominio in url for dominio in DOMINIOS_DE_LOGIN):
                pronto = True
                break
            print("Ainda parece estar na tela de login. Aguardando mais um pouco...")
            page.wait_for_timeout(3000)

        if not pronto:
            print("\nNão consegui confirmar que o login terminou. Cancelei, nada foi salvo.")
            navegador.close()
            return 1

        estado = contexto.storage_state()
        navegador.close()

    # Secret do GitHub tem teto de ~64KB. A sessão inteira (cookies +
    # localStorage de cada origem) passa disso fácil — o grosso é cache de
    # app do próprio Outlook (React, feature flags), que não autentica nada.
    #
    # Mas os cookies sozinhos NÃO bastam: o Outlook web é um app MSAL, e o
    # MSAL guarda o próprio cache de token (o que de fato autentica as
    # chamadas à API do correio) em localStorage, sob chaves "msal.*". Medido
    # ao vivo em 31/08/2026: mesmo só essas chaves passaram de 75KB, porque a
    # caixa do Outlook pede token pra vários recursos (substrate, graph,
    # exchange...) e cada um vira uma entrada "accesstoken" própria, grande e
    # de vida curta (renovam sozinhas). O que precisa durar semanas é o
    # "refreshtoken" (um só, usado pra pedir qualquer access token de novo) e
    # a conta/idtoken que o MSAL usa pra saber quem está logado — dropar só
    # as entradas "accesstoken" é seguro: o MSAL trata cache-miss de access
    # token como normal e pede um novo sozinho via refresh token, sem
    # precisar de tela nem de MFA.
    origens_filtradas = []
    for origem in estado.get("origins", []):
        chaves_msal = [
            item for item in origem.get("localStorage", [])
            if "msal" in item.get("name", "").lower()
            and "accesstoken" not in item.get("name", "").lower()
        ]
        if chaves_msal:
            origens_filtradas.append({
                "origin": origem["origin"],
                "localStorage": chaves_msal,
            })
    estado_compacto = {
        "cookies": estado.get("cookies", []),
        "origins": origens_filtradas,
    }
    valor = json.dumps(estado_compacto)
    total_chaves_msal = sum(len(o["localStorage"]) for o in origens_filtradas)
    print(
        f"\nSessão inteira tinha {len(json.dumps(estado))} caracteres; cookies + "
        f"{total_chaves_msal} chave(s) msal (o que autentica de verdade) ficaram "
        f"em {len(valor)}. Gravando no cofre do GitHub..."
    )
    if len(valor) > 60000:
        print(
            "  aviso: passou de 60000 caracteres, perto do teto de ~64KB do "
            "Secret. Pode falhar ao gravar — se falhar, avise, não dá pra "
            "cortar sem risco de perder o que autentica."
        )
    ok = gravar("OUTLOOK_STORAGE_STATE", valor)
    valor = None  # some da memória assim que possível
    if not ok:
        return 1

    print("\nPronto. O robô já pode ler o Outlook institucional.")
    print('Quando a sessão vencer, a fonte "outlook" do guia vai avisar')
    print("sozinha (fica em falhou); aí é só rodar este script de novo.\n")
    return 0


if __name__ == "__main__":
    codigo = main()
    input("\nPressione ENTER pra fechar esta janela...")
    sys.exit(codigo)
