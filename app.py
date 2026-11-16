"""Telas do Cursor — consulta local, isolada do KaptureAGDev.

Uso, a partir desta pasta:

    streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from export_formats import ExportError, build_download, events_html
from reader import sessions

st.set_page_config(
    page_title="Telas do Cursor",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.4rem; max-width: 92rem; }
    .ev { margin: 0.7rem 0; padding: 0.7rem 0.85rem; background: #1e293b; border-radius: 0.6rem; }
    .ev header { display: flex; gap: 0.75rem; align-items: baseline; }
    .tag { font-size: 0.75rem; letter-spacing: 0.03em; text-transform: uppercase; color: #7dd3fc; }
    .ev.comment .tag { color: #cbd5e1; }
    .ev.command .tag { color: #6ee7b7; }
    .ev.tool .tag, .ev.subagent .tag { color: #94a3b8; }
    time, .cwd, .detail, .note { color: #94a3b8; }
    .cwd, .detail, time { font-size: 0.85rem; }
    pre { white-space: pre-wrap; word-break: break-word; font-family: Consolas, monospace; font-size: 0.9rem; }
    p { margin: 0.3rem 0; white-space: pre-wrap; }
    .final { margin: 0.4rem 0 0.8rem; padding: 0.75rem 0.9rem; border-left: 3px solid #38bdf8; background: #1e293b; border-radius: 0.5rem; }
    .final span { display: block; color: #7dd3fc; font-size: 0.8rem; }
    div[data-testid="stButton"] button { text-align: left; white-space: normal; height: auto; }
    </style>
    """,
    unsafe_allow_html=True,
)


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


@st.cache_data(show_spinner="Preparando o arquivo…")
def cached_download(slug: str, session_id: str, updated_at: str, label: str, fmt: str):
    detail = load_detail(slug, session_id, updated_at, True)
    return build_download(detail, {"slug": slug, "label": label}, fmt)


def main() -> None:
    st.title("Telas do Cursor")
    st.caption(
        "Escolha a pasta que corresponde ao Folder aberto no Cursor. "
        "A lista mostra cada tela de agente, os comandos e o comentário final, lidos neste computador. "
        "Este aplicativo não grava no KaptureNOTES."
    )

    with st.sidebar:
        st.header("Folder")
        query = st.text_input("Filtrar pasta", placeholder="Nome do projeto ou caminho")
        include_temporary = st.checkbox("Incluir pastas temporárias")
        if st.button("Atualizar", use_container_width=True):
            load_folders.clear()
            load_session_list.clear()
            load_detail.clear()
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
        st.info(note or "Nenhuma tela de agente encontrada nas pastas do Cursor deste computador.")
        return

    labels = {item["slug"]: f"{item.get('label') or item['slug']} ({item.get('sessions') or 0})" for item in shown}
    options = [item["slug"] for item in shown]
    if st.session_state.get("folder_choice") not in options:
        st.session_state["folder_choice"] = options[0]
    slug = st.sidebar.selectbox(
        "Folder",
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

    search = st.text_input("Buscar na pasta", placeholder="Pedido, comando ou comentário")
    term = search.strip().casefold()
    found = []
    for item in payload.get("sessions") or []:
        blob = "\n".join(
            [item.get("title") or "", item.get("last_comment") or "", *(item.get("command_preview") or [])]
        ).casefold()
        if not term or term in blob:
            found.append(item)

    list_col, detail_col = st.columns([1, 1.7], gap="medium")
    with list_col:
        st.subheader(f"Conversas ({len(found)})")
        if not found:
            st.caption("Nenhuma tela nesta pasta.")
        with st.container(height=680):
            for item in found:
                active = item["id"] == st.session_state.get("session_id")
                caption = (
                    f"{item.get('title') or '(sem pedido)'}\n\n"
                    f"{item.get('updated_at') or ''} · "
                    f"{item.get('user_turns') or 0} pedidos · "
                    f"{item.get('commands') or 0} comandos · "
                    f"{item.get('comments') or 0} comentários"
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


def _render_detail(folder: dict, found: list[dict]) -> None:
    session_id = st.session_state.get("session_id") or ""
    current = next((item for item in found if item["id"] == session_id), None)
    if current is None:
        st.subheader("Conversa")
        st.caption("Escolha uma tela para ver pedidos, comandos e comentários.")
        return

    try:
        detail = load_detail(folder["slug"], current["id"], current.get("updated_at") or "", False)
    except sessions.CursorSessionsError as exc:
        st.error(exc.detail)
        return

    session = detail.get("session") or current
    st.subheader(session.get("title") or "(sem pedido)")
    meta = session.get("started_at") or session.get("updated_at") or ""
    if session.get("subagents"):
        meta = f"{meta} · {session['subagents']} agente(s) auxiliar(es)"
    st.caption(meta)

    _export_bar(folder, current)

    final = (session.get("last_comment") or "").strip()
    if final:
        st.html(f"<div class=\"final\"><span>Comentário final</span><p>{_plain(final)}</p></div>")

    view = st.radio(
        "Filtro",
        options=("conversation", "user", "comment", "command"),
        format_func=lambda item: {
            "conversation": "Conversa",
            "user": "Pedido",
            "comment": "Comentário",
            "command": "Comando",
        }[item],
        horizontal=True,
        label_visibility="collapsed",
    )
    show_tools = st.checkbox("Mostrar leituras e buscas")
    visible = [
        event
        for event in detail.get("events") or []
        if _visible(event, view, show_tools)
    ]
    if session.get("truncated"):
        st.caption(
            "Trechos do meio foram omitidos na tela. "
            "O arquivo exportado leva a conversa inteira, e o comentário final permanece acima."
        )
    st.html(events_html(visible))


def _export_bar(folder: dict, summary: dict) -> None:
    st.markdown("**Exportar esta conversa**")
    columns = st.columns(3)
    for column, fmt, label in zip(columns, ("html", "markdown", "pdf"), ("HTML", "Markdown", "PDF")):
        with column:
            try:
                data, name, mime = cached_download(
                    folder["slug"],
                    summary["id"],
                    summary.get("updated_at") or "",
                    folder.get("label") or folder["slug"],
                    fmt,
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
            )


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
