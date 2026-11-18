"""Consulta somente leitura do chat do VS Code.

As sessões do Copilot Chat ficam em
%APPDATA%/Code/User/globalStorage/github.copilot-chat/session-store.db.
O banco é aberto só para leitura.
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from cursor_agent_sessions import (
    COMMENT_LIMIT,
    EVENT_LIMIT,
    HEAD_KEEP,
    TEXT_LIMIT,
    TITLE_LIMIT,
    CursorSessionsError,
    _clip,
    _event,
)

ROOT_ENV = "VSCODE2NOTES_DB"
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def vscode_db() -> Path:
    raw = os.environ.get(ROOT_ENV, "").strip()
    if raw:
        return Path(raw)
    appdata = os.environ.get("APPDATA", "").strip()
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / "Code" / "User" / "globalStorage" / "github.copilot-chat" / "session-store.db"


def _conectar(caminho: Path) -> sqlite3.Connection:
    uri = "file:" + caminho.resolve().as_posix() + "?mode=ro"
    try:
        conexao = sqlite3.connect(uri, uri=True, timeout=1)
    except sqlite3.Error as exc:
        raise CursorSessionsError("Não foi possível ler o banco do VS Code.", 404) from exc
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA query_only = ON")
    return conexao


def _hora(valor) -> str:
    if not isinstance(valor, str) or not valor:
        return ""
    texto = valor.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", texto):
        return texto[:19]
    try:
        quando = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return quando.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _slug(rotulo: str, usados: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", rotulo).strip("-")[:160] or "vscode"
    slug = base
    numero = 2
    while slug in usados:
        slug = f"{base}-{numero}"[:180]
        numero += 1
    usados.add(slug)
    return slug


def _rotulo(linha: sqlite3.Row) -> str:
    repositorio = str(linha["repository"] or "").strip()
    pasta = str(linha["cwd"] or "").strip()
    return repositorio or pasta or "VS Code"


def _carregar(caminho: Path) -> list[dict]:
    if not caminho.is_file():
        return []
    try:
        conexao = _conectar(caminho)
    except CursorSessionsError:
        raise
    try:
        sessoes = list(
            conexao.execute(
                "SELECT id, cwd, repository, summary, created_at, updated_at FROM sessions"
            )
        )
        turnos = list(
            conexao.execute(
                """
                SELECT session_id, turn_index, user_message, assistant_response, timestamp
                FROM turns
                ORDER BY session_id, turn_index
                """
            )
        )
    except sqlite3.Error as exc:
        raise CursorSessionsError("Não foi possível ler as sessões do VS Code.", 404) from exc
    finally:
        conexao.close()
    por_sessao: dict[str, list[sqlite3.Row]] = {}
    for turno in turnos:
        por_sessao.setdefault(str(turno["session_id"]), []).append(turno)
    usados: set[str] = set()
    grupos: dict[str, str] = {}
    for linha in sorted(sessoes, key=lambda item: _rotulo(item)):
        rotulo = _rotulo(linha)
        if rotulo not in grupos:
            grupos[rotulo] = _slug(rotulo, usados)
    saida = []
    for linha in sessoes:
        identificador = str(linha["id"] or "")
        if not UUID_RE.match(identificador):
            continue
        rotulo = _rotulo(linha)
        eventos = _eventos(por_sessao.get(identificador, []))
        saida.append(
            {
                "id": identificador,
                "slug": grupos[rotulo],
                "label": rotulo,
                "path": rotulo if rotulo != "VS Code" else None,
                "summary": str(linha["summary"] or "").strip(),
                "created_at": _hora(linha["created_at"]),
                "updated_at": _hora(linha["updated_at"]) or _hora(linha["created_at"]),
                "events": eventos,
            }
        )
    return saida


def _eventos(turnos: list[sqlite3.Row]) -> list[dict]:
    feitos: list[dict] = []
    for turno in turnos:
        quando = _hora(turno["timestamp"])
        pedido = turno["user_message"]
        if isinstance(pedido, str) and pedido.strip():
            feitos.append(_event("user", _clip(pedido, TEXT_LIMIT), at=quando))
        resposta = turno["assistant_response"]
        if isinstance(resposta, str) and resposta.strip():
            feitos.append(_event("comment", _clip(resposta, TEXT_LIMIT), at=quando))
    return feitos


def _resumo(sessao: dict) -> dict:
    eventos = sessao["events"]
    titulo = sessao["summary"]
    inicio = ""
    ultimo = ""
    usuarios = comentarios = 0
    for evento in eventos:
        if evento["kind"] == "user":
            usuarios += 1
            if not inicio:
                inicio = evento.get("at") or ""
            if not titulo and evento["text"]:
                titulo = evento["text"].splitlines()[0]
        elif evento["kind"] == "comment" and evento["text"]:
            comentarios += 1
            ultimo = evento["text"]
    return {
        "id": sessao["id"],
        "title": _clip(titulo or "(sem pedido)", TITLE_LIMIT),
        "started_at": inicio or sessao["created_at"],
        "updated_at": sessao["updated_at"],
        "user_turns": usuarios,
        "comments": comentarios,
        "commands": 0,
        "last_comment": _clip(ultimo, COMMENT_LIMIT),
        "command_preview": [],
        "subagents": 0,
    }


def _pastas(sessoes: list[dict]) -> list[dict]:
    grupos: dict[str, dict] = {}
    for sessao in sessoes:
        pasta = grupos.setdefault(
            sessao["slug"],
            {
                "slug": sessao["slug"],
                "label": sessao["label"],
                "path": sessao["path"],
                "kind": "workspace",
                "sessions": 0,
                "updated_at": "",
            },
        )
        pasta["sessions"] += 1
        if (sessao["updated_at"] or "") > (pasta["updated_at"] or ""):
            pasta["updated_at"] = sessao["updated_at"]
    return sorted(grupos.values(), key=lambda item: item["updated_at"] or "", reverse=True)


def list_folders(*, include_temporary: bool = False, root: Path | None = None) -> dict:
    del include_temporary
    caminho = root or vscode_db()
    payload = {"root": str(caminho), "folders": [], "note": ""}
    if not caminho.is_file():
        payload["note"] = "Nenhuma conversa do VS Code encontrada neste computador."
        return payload
    sessoes = _carregar(caminho)
    if not sessoes:
        payload["note"] = "Nenhuma conversa do VS Code encontrada neste computador."
        return payload
    payload["folders"] = _pastas(sessoes)
    return payload


def list_sessions(slug: str, root: Path | None = None) -> dict:
    sessoes = [item for item in _carregar(root or vscode_db()) if item["slug"] == slug]
    if not sessoes:
        raise CursorSessionsError("Pasta não encontrada.", 404)
    lista = [_resumo(item) for item in sessoes]
    lista.sort(key=lambda item: item["updated_at"] or "", reverse=True)
    return {
        "folder": {
            "slug": slug,
            "label": sessoes[0]["label"],
            "path": sessoes[0]["path"],
            "kind": "workspace",
        },
        "sessions": lista,
    }


def _limitar(eventos: list[dict], full: bool) -> tuple[list[dict], bool, int]:
    if full or len(eventos) <= EVENT_LIMIT:
        return eventos, False, 0
    omitidos = len(eventos) - EVENT_LIMIT
    return eventos[:HEAD_KEEP] + eventos[-(EVENT_LIMIT - HEAD_KEEP) :], True, omitidos


def session_detail(slug: str, session_id: str, root: Path | None = None, *, full: bool = False) -> dict:
    if not UUID_RE.match(session_id or ""):
        raise CursorSessionsError("Conversa inválida.", 400)
    alvo = next(
        (
            item
            for item in _carregar(root or vscode_db())
            if item["slug"] == slug and item["id"].lower() == session_id.lower()
        ),
        None,
    )
    if alvo is None:
        raise CursorSessionsError("Conversa não encontrada.", 404)
    eventos, truncado, omitidos = _limitar(alvo["events"], full)
    for indice, evento in enumerate(eventos, start=1):
        evento["seq"] = indice
    resumo = _resumo(alvo)
    resumo["truncated"] = truncado
    resumo["omitted"] = omitidos
    return {"session": resumo, "events": eventos}
