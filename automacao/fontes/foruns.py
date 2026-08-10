# -*- coding: utf-8 -*-
"""Leitura incremental de fóruns com prioridade para avisos oficiais."""
import copy
import re
from datetime import datetime, timedelta

from playwright.sync_api import Error as PlaywrightError

from configuracao import (
    BR_TZ,
    JANELA_AVISOS_DIAS,
    MAX_POSTS_POR_DISCUSSAO,
    NOVO_ATE_DIAS,
    TRECHO_AVISO,
    VALIDADE_AUTOR_DIAS,
    VERSAO_CACHE,
)
from dominio.datas import sem_acento
from dominio.prazos import GATILHOS_PRAZO, extrair_prazos
from fontes.moodle import FalhaFonte, navegar_insistindo

JS_DISCUSSOES = """
() => {
  const linhas = [...document.querySelectorAll('tr')].filter(r => r.querySelector('a[href*="discuss.php"]'));
  return linhas.map(r => {
    const a = r.querySelector('a[href*="discuss.php"]');
    const times = [...r.querySelectorAll('time')].map(t => t.getAttribute('datetime')).filter(Boolean);
    return {
      url: a.href.split('#')[0],
      titulo: (a.innerText || '').trim(),
      ultimo: times.length ? times[times.length - 1] : null,
    };
  }).filter(d => d.titulo);
}
"""

JS_POSTS = """
() => {
  const seletores = ['article.forum-post-container', '[data-region="post"]', '.forumpost'];
  let achados = [];
  for (const s of seletores) {
    achados = [...document.querySelectorAll(s)];
    if (achados.length) break;
  }
  return achados.map(p => {
    const autor = p.querySelector('a[href*="user/view"]');
    const t = p.querySelector('time');
    const h = p.querySelector('h3, h4, .subject');
    const body = p.querySelector('[data-region="post-content"], .post-content-container, .posting');
    const brutoId = p.getAttribute('data-post-id') || p.id || '';
    const id = (brutoId.match(/\\d+/) || [null])[0];
    return {
      id: id,
      autor: autor ? autor.innerText.trim() : null,
      data: t ? t.getAttribute('datetime') : null,
      titulo: h ? h.innerText.trim() : null,
      texto: body ? body.innerText.trim() : '',
      links: [...p.querySelectorAll('a[href]')].map(a => a.href)
               .filter(href => href && !href.includes('user/view') && !href.includes('#p')),
    };
  }).filter(p => p.texto);
}
"""

LINKS_QUENTES = (
    "elos.vc",
    "youtube",
    "youtu.be",
    "meet.google",
    "teams.microsoft",
    "zoom.",
)
CHAVES_AVISO = (
    "criterio",
    "avaliacao",
    "organizacao",
    "aviso",
    "comunicado",
    "live",
    "gravacao",
    "representante",
    "peso",
    "prazo",
    "entrega",
    "grupo",
)


def forum_de_avisos(forum):
    return "aviso" in sem_acento(forum.get("label") or "")


def forum_do_grupo(forum):
    rotulo = sem_acento(forum.get("label") or "")
    return bool(re.search(r"\b(grupo|g4)\b", rotulo))


def ordenar_foruns(foruns):
    """Primeira passagem: Avisos; depois grupo; por fim os demais."""

    def prioridade(forum):
        if forum_de_avisos(forum):
            return 0
        if forum_do_grupo(forum):
            return 1
        return 2

    return sorted(enumerate(foruns), key=lambda par: (prioridade(par[1]), par[0]))


def identidade_post(post):
    identificador = post.get("id")
    if identificador is not None and str(identificador).strip():
        return "id", str(identificador).strip()
    return (
        "fallback",
        post.get("data"),
        sem_acento(post.get("autor") or ""),
        (post.get("texto") or "")[:160],
    )


def deduplicar_posts(posts):
    """Desduplica antes de qualquer ordenação ou corte."""
    unicos = {}
    ordem = []
    for post in posts:
        chave = identidade_post(post)
        if chave not in unicos:
            ordem.append(chave)
            unicos[chave] = post
            continue
        existente = unicos[chave]
        # Se duas representações do mesmo nó divergirem, conserva a que traz
        # mais autoridade/evidência em vez de depender do seletor do DOM.
        qualidade_existente = (
            existente.get("autoridade") == "institucional",
            bool(existente.get("prazos")),
            len(existente.get("texto") or ""),
        )
        qualidade_nova = (
            post.get("autoridade") == "institucional",
            bool(post.get("prazos")),
            len(post.get("texto") or ""),
        )
        if qualidade_nova > qualidade_existente:
            unicos[chave] = post
    return [unicos[chave] for chave in ordem]


def priorizar_posts(posts, autores_institucionais, limite=MAX_POSTS_POR_DISCUSSAO):
    """Desduplica, classifica autoridade, ordena e só então aplica o teto."""
    autores = {sem_acento(autor) for autor in autores_institucionais if autor}
    classificados = []
    for original in posts:
        post = copy.deepcopy(original)
        institucional = sem_acento(post.get("autor") or "") in autores
        post["autoridade"] = "institucional" if institucional else "colega"
        if not institucional:
            for prazo in post.get("prazos") or []:
                prazo["confianca"] = "baixa"
        classificados.append(post)

    unicos = deduplicar_posts(classificados)
    # Data decrescente dentro de cada nível; os sorts são estáveis.
    unicos.sort(key=lambda post: post.get("data") or "", reverse=True)
    unicos.sort(
        key=lambda post: (
            0 if post.get("autoridade") == "institucional" else 1,
            0 if post.get("prazos") else 1,
        )
    )
    return unicos[:limite], len(unicos) > limite, unicos


def autores_institucionais_do_forum(forum, posts):
    if not forum_de_avisos(forum):
        return set()
    return {post.get("autor") for post in posts if post.get("autor")}


def normalizar_registro_autores(bruto, hoje):
    """Aceita o formato antigo (lista) e devolve o novo (nome -> visto em).

    O registro só crescia: quem postasse uma vez num fórum "Avisos" virava
    fonte oficial para sempre, e as datas dessa pessoa passavam a valer como
    confiança alta. Guardar quando cada autor foi visto permite esquecer.
    """
    if isinstance(bruto, dict):
        return dict(bruto)
    return {nome: hoje.isoformat() for nome in (bruto or [])}


def esquecer_autores_antigos(registro, hoje, dias=VALIDADE_AUTOR_DIAS):
    corte = (hoje - timedelta(days=dias)).isoformat()
    return {
        nome: visto
        for nome, visto in registro.items()
        if (visto or "") >= corte
    }


def acumular_autores_institucionais(estado, curso_id, forum, posts, hoje):
    """Acumula autores vistos em Avisos, com validade."""
    chave_curso = str(curso_id or "__sem_curso__")
    por_curso = estado.setdefault("_autores_institucionais", {})
    registro = normalizar_registro_autores(por_curso.get(chave_curso), hoje)
    for autor in autores_institucionais_do_forum(forum, posts):
        registro[autor] = hoje.isoformat()
    registro = esquecer_autores_antigos(registro, hoje)
    por_curso[chave_curso] = registro
    return set(registro)


def post_interessa(post):
    if post.get("autoridade") == "institucional":
        return True
    alvo = sem_acento(post.get("texto", ""))[:800]
    titulo = sem_acento(post.get("titulo", ""))
    if any(gatilho in alvo for gatilho in GATILHOS_PRAZO):
        return True
    if any(
        quente in (link or "")
        for link in post.get("links", [])
        for quente in LINKS_QUENTES
    ):
        return True
    return any(chave in titulo or chave in alvo for chave in CHAVES_AVISO)


def preparar(post, rotulo_forum, url, titulo_alternativo, hoje):
    preparado = dict(post)
    preparado["forum"] = rotulo_forum
    preparado["url"] = url
    preparado["titulo"] = preparado.get("titulo") or titulo_alternativo
    try:
        referencia = datetime.fromisoformat(preparado["data"])
    except (KeyError, TypeError, ValueError):
        referencia = datetime(hoje.year, hoje.month, hoje.day, tzinfo=BR_TZ)
    preparado["prazos"] = extrair_prazos(
        preparado.get("texto", ""), referencia
    )
    preparado["texto"] = (preparado.get("texto") or "")[:TRECHO_AVISO]
    preparado["links"] = [
        link for link in (preparado.get("links") or []) if link
    ][:6]
    preparado.pop("url_forum", None)
    return preparado


def varrer_foruns(
    page,
    foruns,
    estado,
    orcamento,
    hoje,
    diagnostico=None,
    curso_id=None,
):
    """Lê avisos/grupo primeiro e acumula autores oficiais por disciplina."""
    coletados = []
    listas_live = falhas = pulados_orcamento = cache_em_falha = 0
    truncado = False
    institucionais_vistos = institucionais_guardados = 0
    chave_curso = str(curso_id or "__sem_curso__")
    autores_por_curso = estado.setdefault("_autores_institucionais", {})
    registro_autores = esquecer_autores_antigos(
        normalizar_registro_autores(
            autores_por_curso.get(chave_curso), hoje
        ),
        hoje,
    )
    autores_por_curso[chave_curso] = registro_autores
    autores = set(registro_autores)

    def atualizar_autores(forum, posts):
        autores.update(
            acumular_autores_institucionais(
                estado, chave_curso, forum, posts, hoje
            )
        )

    def normalizar_cache(posts):
        guardados, _, _ = priorizar_posts(
            posts, autores, MAX_POSTS_POR_DISCUSSAO
        )
        return guardados

    def usar_cache(cache):
        nonlocal truncado, institucionais_vistos, institucionais_guardados
        posts = cache.get("posts", [])
        institucionais = sum(
            post.get("autoridade") == "institucional" for post in posts
        )
        institucionais_vistos += int(
            cache.get("posts_institucionais_vistos", institucionais) or 0
        )
        institucionais_guardados += int(
            cache.get("posts_institucionais_guardados", institucionais) or 0
        )
        truncado = truncado or bool(cache.get("truncado"))
        return normalizar_cache(posts)

    def guardar(chave, ultimo, posts):
        nonlocal truncado, institucionais_vistos, institucionais_guardados
        guardados, cortou, todos = priorizar_posts(
            posts, autores, MAX_POSTS_POR_DISCUSSAO
        )
        vistos_inst = sum(
            post.get("autoridade") == "institucional" for post in todos
        )
        guardados_inst = sum(
            post.get("autoridade") == "institucional" for post in guardados
        )
        institucionais_vistos += vistos_inst
        institucionais_guardados += guardados_inst
        truncado = truncado or cortou
        if cortou:
            print(
                f"    aviso: {len(todos)} posts relevantes, guardando "
                f"{MAX_POSTS_POR_DISCUSSAO} após priorizar autoridade "
                f"em {chave[-46:]}"
            )
        estado[chave] = {
            "schema_version": VERSAO_CACHE,
            "ultimo": ultimo or "",
            "truncado": cortou,
            "posts_institucionais_vistos": vistos_inst,
            "posts_institucionais_guardados": guardados_inst,
            "posts": guardados,
        }
        return guardados

    for _, forum in ordenar_foruns(foruns):
        cache_forum = estado.get(forum["url"], {})
        if orcamento <= 0:
            atualizar_autores(forum, cache_forum.get("posts", []))
            coletados.extend(usar_cache(cache_forum))
            pulados_orcamento += 1
            continue
        try:
            navegar_insistindo(
                page,
                forum["url"],
                espera_ms=700,
                rotulo=f"fórum {forum.get('label') or forum['url']}",
            )
            orcamento -= 1
            listas_live += 1
        except (PlaywrightError, TimeoutError, FalhaFonte) as erro:
            print(f"  falha ao ler o fórum {forum.get('label')}: {erro}")
            atualizar_autores(forum, cache_forum.get("posts", []))
            coletados.extend(usar_cache(cache_forum))
            falhas += 1
            cache_em_falha += int(bool(cache_forum.get("posts")))
            continue

        try:
            aqui = page.evaluate(JS_POSTS)
        except PlaywrightError:
            aqui = []
            falhas += 1
        try:
            discussoes = page.evaluate(JS_DISCUSSOES)
        except PlaywrightError:
            discussoes = []
            falhas += 1

        if aqui and not discussoes:
            atualizar_autores(forum, aqui)
            mais_novo = max((post.get("data") or "") for post in aqui)
            if (
                mais_novo > (cache_forum.get("ultimo") or "")
                or "posts" not in cache_forum
                or cache_forum.get("schema_version") != VERSAO_CACHE
            ):
                preparados = [
                    preparar(
                        post,
                        forum["label"],
                        forum["url"],
                        forum["label"],
                        hoje,
                    )
                    for post in aqui
                ]
                classificados, _, _ = priorizar_posts(
                    preparados, autores, len(preparados) or 1
                )
                bons = [
                    post for post in classificados if post_interessa(post)
                ]
                coletados.extend(guardar(forum["url"], mais_novo, bons))
            else:
                atualizar_autores(forum, cache_forum.get("posts", []))
                coletados.extend(usar_cache(cache_forum))
            continue

        for discussao in discussoes:
            cache = estado.get(discussao["url"], {})
            parada = (
                cache.get("ultimo")
                and discussao.get("ultimo")
                and discussao["ultimo"] <= cache["ultimo"]
                and "posts" in cache
                and cache.get("schema_version") == VERSAO_CACHE
            )
            if parada or orcamento <= 0:
                atualizar_autores(forum, cache.get("posts", []))
                coletados.extend(usar_cache(cache))
                if orcamento <= 0:
                    pulados_orcamento += 1
                continue
            try:
                navegar_insistindo(
                    page,
                    discussao["url"],
                    espera_ms=600,
                    rotulo=f"discussão {discussao.get('titulo') or ''}".strip(),
                )
                orcamento -= 1
                posts = page.evaluate(JS_POSTS)
            except (PlaywrightError, TimeoutError, FalhaFonte) as erro:
                print(
                    f"  falha na discussão {discussao.get('titulo')}: {erro}"
                )
                atualizar_autores(forum, cache.get("posts", []))
                coletados.extend(usar_cache(cache))
                falhas += 1
                cache_em_falha += int(bool(cache.get("posts")))
                continue
            atualizar_autores(forum, posts)
            preparados = [
                preparar(
                    post,
                    forum["label"],
                    discussao["url"],
                    discussao.get("titulo"),
                    hoje,
                )
                for post in posts
            ]
            classificados, _, _ = priorizar_posts(
                preparados, autores, len(preparados) or 1
            )
            bons = [post for post in classificados if post_interessa(post)]
            coletados.extend(
                guardar(discussao["url"], discussao.get("ultimo"), bons)
            )

    corte = (hoje - timedelta(days=JANELA_AVISOS_DIAS)).isoformat()
    recente = (hoje - timedelta(days=NOVO_ATE_DIAS)).isoformat()
    saida, vistos = [], set()
    for post in coletados:
        data = (post.get("data") or "")[:10]
        if data < corte:
            continue
        chave = identidade_post(post)
        if chave in vistos:
            continue
        vistos.add(chave)
        post["novo"] = data >= recente
        saida.append(post)
    saida.sort(key=lambda post: post.get("data") or "", reverse=True)

    if diagnostico is not None:
        if not foruns:
            status = "nao_aplicavel"
        elif falhas and not listas_live:
            status = "falhou"
        elif falhas:
            status = "degradado"
        elif pulados_orcamento:
            status = "parcial"
        else:
            status = "live"
        diagnostico.update(
            {
                "status": status,
                "foruns": len(foruns),
                "listas_live": listas_live,
                "falhas": falhas,
                "pulados_orcamento": pulados_orcamento,
                "cache_usado_em_falha": cache_em_falha,
                "truncado": truncado,
                "autores_institucionais": len(autores),
                "posts_institucionais_vistos": institucionais_vistos,
                "posts_institucionais_guardados": institucionais_guardados,
            }
        )
    return saida, orcamento
