"""Consulta somente leitura das conversas do Claude Code.

Cada projeto fica em ~/.claude/projects/<slug>/, com uma conversa por arquivo
<id>.jsonl. Subagentes, quando existirem, ficam em <id>/subagents/.
A interface é a mesma de cursor_agent_sessions.py, para o app tratar as origens igual.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

from cursor_agent_sessions import (
    COMMAND_LIMIT,
    COMMENT_LIMIT,
    EVENT_LIMIT,
    HEAD_KEEP,
    LIST_COMMANDS,
    SESSION_RE,
    SLUG_RE,
    TEXT_LIMIT,
    TITLE_LIMIT,
    CursorSessionsError,
    _clip,
    _event,
    _iso,
)

ROOT_ENV = "CLAUDE2NOTES_PROJECTS_ROOT"
COMMAND_TOOLS = frozenset({"Bash", "PowerShell"})
RESUMO_CAMPOS = ("file_path", "path", "pattern", "subject", "description", "query", "url")


def claude_projects_root() -> Path:
    raw = os.environ.get(ROOT_ENV, "").strip()
    if raw:
        return Path(raw)
    return Path.home() / ".claude" / "projects"


def folder_kind(slug: str) -> str:
    low = slug.lower()
    if "appdata-local-temp" in low or "worktrees" in low:
        return "temporary"
    return "workspace"


def _pasta(slug: str, root: Path | None = None) -> Path:
    if not SLUG_RE.match(slug or ""):
        raise CursorSessionsError("Pasta inválida.", 400)
    base = (root or claude_projects_root()).resolve()
    if not base.is_dir():
        raise CursorSessionsError("Armazenamento local do Claude Code não encontrado.", 404)
    candidate = (base / slug).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise CursorSessionsError("Pasta fora do armazenamento local do Claude Code.", 400) from exc
    if not candidate.is_dir():
        raise CursorSessionsError("Pasta não encontrada.", 404)
    return candidate


def _session_files(folder: Path) -> list[Path]:
    try:
        children = list(folder.iterdir())
    except OSError:
        return []
    found = [p for p in children if p.is_file() and p.suffix == ".jsonl" and SESSION_RE.match(p.stem)]
    return sorted(found, key=lambda p: p.name)


def _arquivo_sessao(folder: Path, session_id: str) -> Path:
    wanted = session_id.lower()
    for path in _session_files(folder):
        if path.stem.lower() == wanted:
            return path
    raise CursorSessionsError("Conversa não encontrada.", 404)


def _subagentes(folder: Path, session_id: str) -> list[Path]:
    pasta = folder / session_id / "subagents"
    if not pasta.is_dir():
        return []
    return sorted(pasta.glob("*.jsonl"))


def _rows(path: Path, limit: int | None = None):
    try:
        handle = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return
    with handle:
        for numero, line in enumerate(handle):
            if limit is not None and numero >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                yield row


def _cwd(folder: Path) -> str:
    for path in _session_files(folder)[:3]:
        for row in _rows(path, limit=50):
            cwd = row.get("cwd")
            if isinstance(cwd, str) and cwd.strip():
                return cwd.strip()
    return ""


def _hora(valor) -> str:
    if not isinstance(valor, str) or not valor:
        return ""
    try:
        quando = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return quando.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _conteudo(row: dict) -> list[dict]:
    message = row.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [bloco for bloco in content if isinstance(bloco, dict)]
    return []


def _resumo_ferramenta(nome: str, entrada: dict) -> str:
    for campo in RESUMO_CAMPOS:
        valor = entrada.get(campo)
        if isinstance(valor, str) and valor.strip():
            return _clip(f"{nome}: {valor.strip()}", 300)
    return _clip(nome, 300)


def _ferramenta(bloco: dict, at: str, subagent: str) -> dict:
    nome = str(bloco.get("name") or "tool")
    entrada = bloco.get("input") if isinstance(bloco.get("input"), dict) else {}
    if nome in COMMAND_TOOLS:
        return _event(
            "command",
            _clip(str(entrada.get("command") or ""), COMMAND_LIMIT),
            detail=_clip(str(entrada.get("description") or ""), 240),
            tool=nome,
            at=at,
            subagent=subagent,
        )
    return _event("tool", _resumo_ferramenta(nome, entrada), tool=nome, at=at, subagent=subagent)


def _events_from_row(row: dict, subagent: str) -> list[dict]:
    tipo = row.get("type")
    if tipo not in {"user", "assistant"} or row.get("isMeta"):
        return []
    at = _hora(row.get("timestamp"))
    sub = subagent or ("sidechain" if row.get("isSidechain") else "")
    if tipo == "user":
        texto = "\n".join(
            str(bloco.get("text") or "") for bloco in _conteudo(row) if bloco.get("type") == "text"
        )
        texto = _clip(texto, TEXT_LIMIT)
        return [_event("user", texto, at=at, subagent=sub)] if texto else []
    made: list[dict] = []
    for bloco in _conteudo(row):
        kind = bloco.get("type")
        if kind == "thinking":
            texto = _clip(str(bloco.get("thinking") or ""), TEXT_LIMIT)
            if texto:
                made.append(_event("thinking", texto, at=at, subagent=sub))
        elif kind == "text":
            texto = _clip(str(bloco.get("text") or ""), TEXT_LIMIT)
            if texto:
                made.append(_event("comment", texto, at=at, subagent=sub))
        elif kind == "tool_use":
            made.append(_ferramenta(bloco, at, sub))
    return made


def _parse(path: Path, subagent: str = "") -> tuple[list[dict], str]:
    events: list[dict] = []
    titulo = ""
    for row in _rows(path):
        if row.get("type") == "ai-title":
            if not titulo:
                titulo = str(row.get("aiTitle") or "").strip()
            continue
        events.extend(_events_from_row(row, subagent))
    return events, titulo


def _events_for(path: Path, subagent: str = "", limit: int | None = EVENT_LIMIT) -> tuple[list[dict], bool, int]:
    events, _ = _parse(path, subagent)
    if limit is None or len(events) <= limit:
        return events, False, 0
    omitted = len(events) - limit
    return events[:HEAD_KEEP] + events[-(limit - HEAD_KEEP):], True, omitted


def _resumo(path: Path, events: list[dict], titulo: str) -> dict:
    title = titulo
    started = ""
    last_comment = ""
    users = comments = commands = 0
    command_preview: list[str] = []
    for event in events:
        kind = event["kind"]
        if kind == "user":
            users += 1
            if not started:
                started = event.get("at") or ""
            if not title and event["text"]:
                title = _clip(event["text"].splitlines()[0], TITLE_LIMIT)
        elif kind == "comment" and event["text"]:
            comments += 1
            last_comment = event["text"]
        elif kind == "command":
            commands += 1
            if len(command_preview) < LIST_COMMANDS and event["text"]:
                command_preview.append(_clip(event["text"].splitlines()[0], 180))
    return {
        "id": path.stem,
        "title": title or "(sem pedido)",
        "started_at": started,
        "updated_at": _iso(path.stat().st_mtime),
        "user_turns": users,
        "comments": comments,
        "commands": commands,
        "last_comment": _clip(last_comment, COMMENT_LIMIT),
        "command_preview": command_preview,
    }


def list_folders(*, include_temporary: bool = False, root: Path | None = None) -> dict:
    base = root or claude_projects_root()
    payload = {"root": str(base), "folders": [], "note": ""}
    if not base.is_dir():
        payload["note"] = "Nenhuma pasta do Claude Code encontrada neste computador."
        return payload
    folders = []
    for child in base.iterdir():
        if not child.is_dir() or not SLUG_RE.match(child.name):
            continue
        kind = folder_kind(child.name)
        if kind != "workspace" and not include_temporary:
            continue
        sessions = _session_files(child)
        if not sessions:
            continue
        cwd = _cwd(child)
        folders.append(
            {
                "slug": child.name,
                "label": cwd or child.name,
                "path": cwd or None,
                "kind": kind,
                "sessions": len(sessions),
                "updated_at": _iso(max(p.stat().st_mtime for p in sessions)),
            }
        )
    folders.sort(key=lambda item: item["updated_at"] or "", reverse=True)
    payload["folders"] = folders
    return payload


def list_sessions(slug: str, root: Path | None = None) -> dict:
    folder = _pasta(slug, root)
    sessions = []
    for path in _session_files(folder):
        events, titulo = _parse(path)
        summary = _resumo(path, events, titulo)
        summary["subagents"] = len(_subagentes(folder, path.stem))
        sessions.append(summary)
    sessions.sort(key=lambda item: item["updated_at"] or "", reverse=True)
    cwd = _cwd(folder)
    return {
        "folder": {
            "slug": slug,
            "label": cwd or slug,
            "path": cwd or None,
            "kind": folder_kind(slug),
        },
        "sessions": sessions,
    }


def session_detail(slug: str, session_id: str, root: Path | None = None, *, full: bool = False) -> dict:
    if not SESSION_RE.match(session_id or ""):
        raise CursorSessionsError("Conversa inválida.", 400)
    folder = _pasta(slug, root)
    path = _arquivo_sessao(folder, session_id)
    limit = None if full else EVENT_LIMIT
    events, truncated, omitted = _events_for(path, limit=limit)
    for sub_path in _subagentes(folder, path.stem):
        events.append(_event("subagent", sub_path.stem, detail="Agente auxiliar desta conversa", tool="subagent"))
        extra, extra_truncated, extra_omitted = _events_for(sub_path, subagent=sub_path.stem, limit=limit)
        events.extend(extra)
        truncated = truncated or extra_truncated
        omitted += extra_omitted
    for index, event in enumerate(events, start=1):
        event["seq"] = index
    events_main, titulo = _parse(path)
    summary = _resumo(path, events_main, titulo)
    summary["subagents"] = len(_subagentes(folder, path.stem))
    summary["truncated"] = truncated
    summary["omitted"] = omitted
    return {"session": summary, "events": events}
