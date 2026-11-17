"""Cursor2Notes — consulta local das conversas do Cursor.

Uso, a partir desta pasta:

    streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

import i18n
import metadados
import temas
from export_formats import ExportError, build_download, events_html
from lote import montar_zip
from metadados import MetadadosError
from reader import sessions

TODAS = "(todas)"

st.set_page_config(
    page_title="Cursor2Notes",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.logo(str(Path(__file__).with_name("assets") / "logo.png"), size="large")


def T(chave: str, **kwargs) -> str:
    """Texto do app no idioma escolhido na barra lateral."""
    return i18n.texto(st.session_state.get("idioma", i18n.PADRAO), chave, **kwargs)


@st.cache_data(show_spinner=False)
def load_folders(include_temporary: bool) -> tuple[list[dict], str]:
    payload = sessions.list_folders(include_temporary=include_temporary)
    return payload.get("folders") or [], payload.get("note") or ""


@st.cache_data(show_spinner=False)
def load_session_list(slug: str) -> dict:
    return sessions.list_sessions(slug)


@st.cache_data(show_spinner=False)
def load_detail(slug: str, session_id: str, updated_at: str, full: bool) -> dict:
    del updated_at
    return sessions.session_detail(slug, session_id, full=full)


@st.cache_data(show_spinner=False)
def cached_download(slug: str, session_id: str, updated_at: str, label: str, fmt: str, tags: tuple, favorita: bool):
    detail = load_detail(slug, session_id, updated_at, True)
    return build_download(detail, {"slug": slug, "label": label}, fmt, list(tags), favorita)


@st.cache_data(show_spinner=False)
def load_temas() -> list[dict]:
    return temas.carregar()


def main() -> None:
    st.session_state.setdefault("tema", temas.TEMA_PADRAO)
    st.session_state.setdefault("idioma", i18n.PADRAO)
    catalogo = temas.por_nome(load_temas())
    tema = catalogo.get(st.session_state["tema"]) or catalogo[temas.TEMA_PADRAO]
    st.markdown(f"<style>{temas.css(tema)}{temas.ESTILO_COMUM}</style>", unsafe_allow_html=True)
    with st.sidebar:
        st.selectbox(
            T("idioma.label"),
            options=list(i18n.IDIOMAS),
            format_func=lambda codigo: i18n.IDIOMAS[codigo],
            key="idioma",
        )
    with st.sidebar.expander(T("tema.aparencia")):
        st.selectbox(
            T("tema.label"),
            options=list(catalogo),
            format_func=lambda nome: temas.rotulo(catalogo[nome]),
            key="tema",
        )
    pagina = st.sidebar.radio(
        T("nav.label"),
        options=["conversas", "ficha"],
        format_func=lambda item: T("nav.conversas" if item == "conversas" else "nav.ficha"),
        key="pagina",
        label_visibility="collapsed",
    )
    if pagina == "ficha":
        _ficha()
        return
    st.title("Cursor2Notes")
    st.caption(f"{T('app.ajuda')} {T('app.lista_ajuda')}")

    with st.sidebar:
        st.header(T("folder.titulo"))
        query = st.text_input(T("folder.filtrar"), placeholder=T("folder.filtrar_placeholder"))
        include_temporary = st.checkbox(T("folder.temporarias"))
        if st.button(T("btn.atualizar"), use_container_width=True):
            load_folders.clear()
            load_session_list.clear()
            load_detail.clear()
            cached_download.clear()
            st.rerun()

    try:
        folders, note = load_folders(include_temporary)
    except sessions.CursorSessionsError as exc:
        st.error(exc.detail)
        return

    needle = query.strip().casefold()
    shown = [
        item
        for item in folders
        if not needle or needle in f"{item.get('label')} {item.get('slug')}".casefold()
    ]
    if not shown:
        st.info(note or T("folder.vazio"))
        return

    labels = {item["slug"]: f"{item.get('label') or item['slug']} ({item.get('sessions') or 0})" for item in shown}
    options = [item["slug"] for item in shown]
    if st.session_state.get("folder_choice") not in options:
        st.session_state["folder_choice"] = options[0]
    slug = st.sidebar.selectbox(
        T("folder.titulo"),
        options=options,
        format_func=lambda item: labels.get(item, item),
        key="folder_choice",
    )
    if st.session_state.get("folder_slug") != slug:
        st.session_state["folder_slug"] = slug
        st.session_state["session_id"] = ""

    folder = next(item for item in shown if item["slug"] == slug)
    try:
        payload = load_session_list(slug)
    except sessions.CursorSessionsError as exc:
        st.error(exc.detail)
        return

    _exportar_pasta(folder, payload)

    try:
        store = metadados.carregar()
    except MetadadosError as exc:
        st.error(str(exc))
        return
    prefixo = f"{slug}|"
    tags_da_pasta = sorted(
        {tag for chave, reg in store["conversas"].items() if chave.startswith(prefixo) for tag in (reg.get("tags") or [])}
    )

    search = st.text_input(T("busca.pasta"), placeholder=T("busca.placeholder"))
    term = search.strip().casefold()
    somente_favoritas = st.sidebar.checkbox(T("filtro.favoritas"))
    tag_filtro = st.sidebar.selectbox(
        T("filtro.tag"),
        options=[TODAS, *tags_da_pasta],
        format_func=lambda valor: T("filtro.todas") if valor == TODAS else valor,
    )
    found = []
    for item in payload.get("sessions") or []:
        blob = "\n".join(
            [item.get("title") or "", item.get("last_comment") or "", *(item.get("command_preview") or [])]
        ).casefold()
        registro = metadados.obter(store, metadados.chave(slug, item["id"]))
        if term and term not in blob:
            continue
        if somente_favoritas and not registro["favorita"]:
            continue
        if tag_filtro != TODAS and tag_filtro not in registro["tags"]:
            continue
        found.append(item)

    list_col, detail_col = st.columns([1, 1.7], gap="medium")
    with list_col:
        st.subheader(T("lista.titulo", n=len(found)))
        if not found:
            st.caption(T("lista.vazia"))
        with st.container(height=680):
            for item in found:
                active = item["id"] == st.session_state.get("session_id")
                registro = metadados.obter(store, metadados.chave(slug, item["id"]))
                marca = "★ " if registro["favorita"] else ""
                tags_txt = " ".join(f"#{tag}" for tag in registro["tags"])
                caption = (
                    f"{marca}{item.get('title') or T('lista.sem_pedido')}\n\n"
                    f"{item.get('updated_at') or ''} · "
                    f"{T('lista.pedidos', n=item.get('user_turns') or 0)} · "
                    f"{T('lista.comandos', n=item.get('commands') or 0)} · "
                    f"{T('lista.comentarios', n=item.get('comments') or 0)}"
                    + (f"\n\n{tags_txt}" if tags_txt else "")
                )
                if st.button(
                    caption,
                    key=f"open-{item['id']}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                ):
                    st.session_state["session_id"] = item["id"]

    with detail_col:
        _render_detail(folder, found)


def _ficha() -> None:
    st.title(T("ficha.titulo"))
    st.markdown(f"`{T('ficha.badge')}`")
    st.write(T("ficha.subtitulo"))
    secoes = [
        (T("ficha.identidade"), [
            (T("ficha.campo.nome"), "Cursor2Notes"),
            (T("ficha.campo.descricao"), T("ficha.valor.descricao")),
            (T("ficha.campo.licenca"), "MIT"),
            (T("ficha.campo.repositorio"), "https://github.com/kaptureiq/Cursor2Notes"),
        ]),
        (T("ficha.stack"), [("Python", "3.11+"), ("Streamlit", "interface web local"), ("fpdf2", "PDF")]),
        (T("ficha.dados"), [
            (T("ficha.campo.origem"), T("ficha.valor.origem")),
            (T("ficha.campo.arquivos"), T("ficha.valor.arquivos")),
            (T("ficha.campo.idiomas"), ", ".join(i18n.IDIOMAS.values())),
        ]),
        (T("ficha.integracoes"), [(T("ficha.integracoes"), T("ficha.valor.integracoes"))]),
        (T("ficha.fronteiras"), [(T("ficha.fronteiras"), T("ficha.valor.fronteiras"))]),
        (T("ficha.operacao"), [(T("ficha.operacao"), T("ficha.valor.operacao"))]),
    ]
    for titulo, campos in secoes:
        st.subheader(titulo)
        for rotulo, valor in campos:
            st.markdown(f"**{rotulo}:** {valor}")


def _render_detail(folder: dict, found: list[dict]) -> None:
    session_id = st.session_state.get("session_id") or ""
    current = next((item for item in found if item["id"] == session_id), None)
    if current is None:
        st.subheader(T("detalhe.titulo"))
        st.caption(T("detalhe.escolha"))
        return

    try:
        detail = load_detail(folder["slug"], current["id"], current.get("updated_at") or "", False)
    except sessions.CursorSessionsError as exc:
        st.error(exc.detail)
        return

    session = detail.get("session") or current
    st.subheader(session.get("title") or T("lista.sem_pedido"))
    meta = session.get("started_at") or session.get("updated_at") or ""
    if session.get("subagents"):
        meta = f"{meta} · {T('detalhe.agentes', n=session['subagents'])}"
    st.caption(meta)

    _export_bar(folder, current)
    _organizacao(folder, current)

    final = (session.get("last_comment") or "").strip()
    if final:
        st.html(f"<div class=\"final\"><span>{T('detalhe.final')}</span><p>{_plain(final)}</p></div>")

    view = st.radio(
        T("detalhe.filtro"),
        options=("conversation", "user", "comment", "command"),
        format_func=lambda item: T({
            "conversation": "vista.conversa",
            "user": "vista.pedido",
            "comment": "vista.comentario",
            "command": "vista.comando",
        }[item]),
        horizontal=True,
        label_visibility="collapsed",
    )
    show_tools = st.checkbox(T("detalhe.ferramentas"))
    visible = [
        event
        for event in detail.get("events") or []
        if _visible(event, view, show_tools)
    ]
    if session.get("truncated"):
        st.caption(f"{T('detalhe.omitidos_tela')} {T('detalhe.omitidos_arquivo')}")
    with st.container(height=680, border=True):
        st.html(events_html(visible))


def _export_bar(folder: dict, summary: dict) -> None:
    st.markdown(f"**{T('export.conversa')}**")
    registro = metadados.obter(metadados.carregar(), metadados.chave(folder["slug"], summary["id"]))
    columns = st.columns(3)
    for column, fmt, label in zip(columns, ("html", "markdown", "pdf"), ("HTML", "Markdown", "PDF")):
        with column:
            try:
                with st.spinner(T("export.preparando")):
                    data, name, mime = cached_download(
                        folder["slug"],
                        summary["id"],
                        summary.get("updated_at") or "",
                        folder.get("label") or folder["slug"],
                        fmt,
                        tuple(registro["tags"]),
                        registro["favorita"],
                    )
            except sessions.CursorSessionsError as exc:
                st.error(exc.detail)
                return
            except ExportError as exc:
                st.error(str(exc))
                continue
            st.download_button(
                label,
                data=data,
                file_name=name,
                mime=mime,
                key=f"dl-{summary['id']}-{fmt}",
                use_container_width=True,
                on_click=_registrar_exportacao,
                args=(folder["slug"], summary["id"], summary.get("updated_at") or "", fmt),
            )


def _exportar_pasta(folder: dict, payload: dict) -> None:
    with st.sidebar.expander(T("export.pasta")):
        formatos = st.multiselect(
            T("export.formatos"),
            options=["html", "md", "pdf"],
            default=["html", "md"],
            format_func=lambda item: {"html": "HTML", "md": "Markdown", "pdf": "PDF"}[item],
        )
        somente_novas = st.checkbox(T("export.so_novas"))
        if st.button(T("export.preparar_zip"), use_container_width=True, disabled=not formatos):
            conversas = []
            with st.spinner(T("export.preparando_zip")):
                for resumo in payload.get("sessions") or []:
                    detalhe = load_detail(folder["slug"], resumo["id"], resumo.get("updated_at") or "", True)
                    conversas.append((resumo, detalhe))
                conteudo, gravados = montar_zip(folder, conversas, formatos, metadados.carregar(), somente_novas)
            st.session_state["zip_pronto"] = {
                "slug": folder["slug"],
                "nome": _nome_zip(folder),
                "dados": conteudo,
                "gravados": gravados,
            }
        pronto = st.session_state.get("zip_pronto")
        if pronto and pronto["slug"] == folder["slug"]:
            st.caption(T("export.arquivos_zip", n=len(pronto["gravados"])))
            st.download_button(
                T("export.baixar_zip"),
                data=pronto["dados"],
                file_name=pronto["nome"],
                mime="application/zip",
                use_container_width=True,
                on_click=_registrar_lote,
                args=(pronto["gravados"],),
            )


def _nome_zip(folder: dict) -> str:
    base = str(folder.get("label") or folder["slug"])
    limpo = "".join("-" if c in '\\/:*?"<>|' else c for c in base).strip(" .-") or "conversas"
    return f"{limpo}.zip"


def _registrar_lote(gravados: list) -> None:
    dados = metadados.carregar()
    for chave, fmt, atualizada in gravados:
        metadados.registrar_exportacao(dados, chave, fmt, atualizada)
    metadados.salvar(dados)


def _registrar_exportacao(slug: str, session_id: str, updated_at: str, fmt: str) -> None:
    dados = metadados.carregar()
    metadados.registrar_exportacao(dados, metadados.chave(slug, session_id), fmt, updated_at)
    metadados.salvar(dados)


def _organizacao(folder: dict, summary: dict) -> None:
    chave = metadados.chave(folder["slug"], summary["id"])
    dados = metadados.carregar()
    registro = metadados.obter(dados, chave)
    st.markdown(f"**{T('org.titulo')}**")
    coluna_fav, coluna_tags = st.columns([1, 3])
    with coluna_fav:
        rotulo = T("org.favorita") if registro["favorita"] else T("org.favoritar")
        if st.button(rotulo, key=f"fav-{summary['id']}", use_container_width=True):
            metadados.alternar_favorita(dados, chave)
            metadados.salvar(dados)
            st.rerun()
    with coluna_tags:
        with st.form(key=f"tags-{summary['id']}", border=False):
            texto = st.text_input(
                T("org.tags"),
                value=", ".join(registro["tags"]),
                placeholder="oracle, migracao, postgres",
            )
            if st.form_submit_button(T("org.salvar_tags")):
                metadados.definir_tags(dados, chave, texto)
                metadados.salvar(dados)
                st.rerun()


def _visible(event: dict, view: str, show_tools: bool) -> bool:
    kind = event.get("kind")
    if kind == "tool" and not show_tools:
        return False
    if view == "conversation":
        return True
    return kind == view


def _plain(text: str) -> str:
    import html as html_lib

    return "<br>".join(html_lib.escape(line) for line in text.splitlines())


main()
