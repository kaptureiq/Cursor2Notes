"""Consulta somente leitura das telas locais do agente Cursor.

Cada Folder aberto no Cursor vira uma pasta em ~/.cursor/projects/<slug>/,
com as conversas em agent-transcripts/<id>/<id>.jsonl.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,240}$")
SESSION_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
USER_QUERY_RE = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.DOTALL)
TIMESTAMP_RE = re.compile(r"<timestamp>\s*(.*?)\s*</timestamp>", re.DOTALL)
TAG_RE = re.compile(r"</?(?:user_query|timestamp)>")

TEXT_LIMIT = 4000
COMMAND_LIMIT = 2000
TITLE_LIMIT = 180
COMMENT_LIMIT = 500
LIST_COMMANDS = 8
EVENT_LIMIT = 2000
HEAD_KEEP = 80

_LARGE_KEYS = frozenset(
    {"contents", "new_string", "old_string", "file_text", "content", "patch", "diff"}
)


class CursorSessionsError(Exception):
    def __init__(self, detail: str, status: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status = status


def cursor_projects_root() -> Path:
    raw = os.environ.get("KAPTURE_CURSOR_PROJECTS_ROOT", "").strip()
    if raw:
        return Path(raw)
    return Path.home() / ".cursor" / "projects"


def _drive_root(letter: str) -> Path:
    return Path(f"{letter.upper()}:/")


def folder_kind(slug: str) -> str:
    low = slug.lower()
    if low in {"empty-window"} or "appdata-local-temp" in low or slug.isdigit():
        return "temporary"
    if re.match(r"^[A-Za-z]-", slug):
        return "workspace"
    return "other"


def _clip(value: str, limit: int) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _contained(root: Path, candidate: Path) -> Path:
    root_r = root.resolve()
    cand = candidate.resolve()
    try:
        cand.relative_to(root_r)
    except ValueError as exc:
        raise CursorSessionsError("Pasta fora do armazenamento local do Cursor.", 400) from exc
    return cand


def project_dir(slug: str, root: Path | None = None) -> Path:
    if not SLUG_RE.match(slug or ""):
        raise CursorSessionsError("Pasta inválida.", 400)
    base = (root or cursor_projects_root()).resolve()
    if not base.is_dir():
        raise CursorSessionsError("Armazenamento local do Cursor não encontrado.", 404)
    candidate = _contained(base, base / slug)
    if not candidate.is_dir():
        raise CursorSessionsError("Pasta não encontrada.", 404)
    return candidate


def resolve_workspace_path(slug: str) -> Path | None:
    match = re.match(r"^([A-Za-z])-(.+)$", slug or "")
    if not match or folder_kind(slug) != "workspace":
        return None
    current = _drive_root(match.group(1))
    if not current.is_dir():
        return None
    remaining = match.group(2)
    while remaining:
        found = _longest_child(current, remaining)
        if not found:
            return None
        name, consumed = found
        current = current / name
        remaining = remaining[consumed:].lstrip("-")
    return current


def _longest_child(directory: Path, remaining: str) -> tuple[str, int] | None:
    try:
        names = [entry.name for entry in directory.iterdir() if entry.is_dir()]
    except OSError:
        return None
    remaining_cf = remaining.casefold()
    best: tuple[str, int] | None = None
    for name in names:
        token = name.replace("\\", "-").replace("/", "-").replace(":", "-")
        token_cf = token.casefold()
        if remaining_cf == token_cf or remaining_cf.startswith(token_cf + "-"):
            if best is None or len(token) > best[1]:
                best = (name, len(token))
    return best


def list_folders(*, include_temporary: bool = False, root: Path | None = None) -> dict:
    base = root or cursor_projects_root()
    payload = {
        "root": str(base),
        "folders": [],
        "note": "",
    }
    if not base.is_dir():
        payload["note"] = "Nenhuma pasta do Cursor encontrada neste computador."
        return payload
    folders = []
    try:
        children = list(base.iterdir())
    except OSError as exc:
        raise CursorSessionsError("Não foi possível ler as pastas do Cursor.", 500) from exc
    for child in children:
        if not child.is_dir():
            continue
        slug = child.name
        if not SLUG_RE.match(slug):
            continue
        kind = folder_kind(slug)
        if kind != "workspace" and not include_temporary:
            continue
        sessions = _session_files(child)
        if not sessions:
            continue
        updated = max(path.stat().st_mtime for path in sessions)
        resolved = resolve_workspace_path(slug) if kind == "workspace" else None
        folders.append(
            {
                "slug": slug,
                "label": str(resolved) if resolved else slug,
                "path": str(resolved) if resolved else None,
                "kind": kind,
                "sessions": len(sessions),
                "updated_at": _iso(updated),
            }
        )
    folders.sort(key=lambda item: item["updated_at"] or "", reverse=True)
    payload["folders"] = folders
    return payload


def list_sessions(slug: str, root: Path | None = None) -> dict:
    folder = project_dir(slug, root)
    sessions = []
    for path in _session_files(folder):
        summary = _summarize_file(path)
        summary["subagents"] = _subagent_count(path)
        sessions.append(summary)
    sessions.sort(key=lambda item: item["updated_at"] or "", reverse=True)
    resolved = resolve_workspace_path(slug)
    return {
        "folder": {
            "slug": slug,
            "label": str(resolved) if resolved else slug,
            "path": str(resolved) if resolved else None,
            "kind": folder_kind(slug),
        },
        "sessions": sessions,
    }


def session_detail(slug: str, session_id: str, root: Path | None = None, *, full: bool = False) -> dict:
    if not SESSION_RE.match(session_id or ""):
        raise CursorSessionsError("Tela inválida.", 400)
    folder = project_dir(slug, root)
    path = _find_session_file(folder, session_id)
    limit = None if full else EVENT_LIMIT
    events, truncated, omitted = _events_for(path, limit=limit)
    for sub_path in _subagent_files(path):
        events.append(
            _event(
                "subagent",
                sub_path.stem,
                detail="Agente auxiliar desta tela",
                tool="subagent",
            )
        )
        extra, extra_truncated, extra_omitted = _events_for(sub_path, subagent=sub_path.stem, limit=limit)
        events.extend(extra)
        truncated = truncated or extra_truncated
        omitted += extra_omitted
    for index, event in enumerate(events, start=1):
        event["seq"] = index
    summary = _summarize_file(path)
    summary["subagents"] = _subagent_count(path)
    summary["truncated"] = truncated
    summary["omitted"] = omitted
    return {"session": summary, "events": events}


def _session_files(project: Path) -> list[Path]:
    base = project / "agent-transcripts"
    if not base.is_dir():
        return []
    found: list[Path] = []
    try:
        children = list(base.iterdir())
    except OSError:
        return []
    for child in children:
        if child.is_dir() and SESSION_RE.match(child.name):
            main = child / f"{child.name}.jsonl"
            if main.is_file():
                found.append(main)
        elif child.is_file() and child.suffix == ".jsonl" and SESSION_RE.match(child.stem):
            found.append(child)
    return found


def _find_session_file(project: Path, session_id: str) -> Path:
    base = project / "agent-transcripts"
    wanted = session_id.lower()
    if not base.is_dir():
        raise CursorSessionsError("Tela não encontrada.", 404)
    for path in _session_files(project):
        if path.stem.lower() == wanted:
            return _contained(project, path)
    raise CursorSessionsError("Tela não encontrada.", 404)


def _subagent_files(main: Path) -> list[Path]:
    folder = main.parent / "subagents"
    if not folder.is_dir():
        return []
    files = [
        path
        for path in folder.glob("*.jsonl")
        if path.is_file() and SESSION_RE.match(path.stem)
    ]
    files.sort(key=lambda path: path.name)
    return files


def _subagent_count(main: Path) -> int:
    return len(_subagent_files(main))


def _summarize_file(path: Path) -> dict:
    events = _parse_events(path)
    title = ""
    started = ""
    last_comment = ""
    users = comments = commands = 0
    command_preview: list[str] = []
    for event in events:
        kind = event["kind"]
        if kind == "user":
            users += 1
            if not title and event["text"]:
                title = _clip(event["text"].splitlines()[0], TITLE_LIMIT)
                started = event.get("at") or ""
        elif kind == "comment" and event["text"]:
            comments += 1
            last_comment = event["text"]
        elif kind == "command":
            commands += 1
            if len(command_preview) < LIST_COMMANDS and event["text"]:
                command_preview.append(_clip(event["text"].splitlines()[0], 180))
    mtime = path.stat().st_mtime
    return {
        "id": path.stem,
        "title": title or "(sem pedido)",
        "started_at": started,
        "updated_at": _iso(mtime),
        "user_turns": users,
        "comments": comments,
        "commands": commands,
        "last_comment": _clip(last_comment, COMMENT_LIMIT),
        "command_preview": command_preview,
    }


def _events_for(path: Path, subagent: str = "", limit: int | None = EVENT_LIMIT) -> tuple[list[dict], bool, int]:
    events = _parse_events(path, subagent=subagent)
    if limit is None or len(events) <= limit:
        return events, False, 0
    omitted = len(events) - limit
    head = events[:HEAD_KEEP]
    tail = events[-(limit - HEAD_KEEP) :]
    kept = head + tail
    for index, event in enumerate(kept, start=1):
        event["seq"] = index
    return kept, True, omitted


def _parse_events(path: Path, subagent: str = "") -> list[dict]:
    events: list[dict] = []
    try:
        handle = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return events
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            events.extend(_events_from_row(row, len(events), subagent))
    return events


def _events_from_row(row: dict, start: int, subagent: str) -> list[dict]:
    role = str(row.get("role") or "")
    blocks = _blocks(row)
    made: list[dict] = []
    if role == "user":
        raw = "\n".join(
            str(block.get("text") or "") for block in blocks if block.get("type") == "text"
        )
        text = _user_text(raw)
        if text:
            made.append(_event("user", text, at=_user_time(raw), subagent=subagent))
        return _number(made, start)
    if role != "assistant":
        return []
    for block in blocks:
        kind = block.get("type")
        if kind == "text":
            text = _clip(str(block.get("text") or ""), TEXT_LIMIT)
            if text:
                made.append(_event("comment", text, subagent=subagent))
        elif kind == "tool_use":
            made.append(_tool_event(block, subagent))
    return _number(made, start)


def _number(events: list[dict], start: int) -> list[dict]:
    for offset, event in enumerate(events, start=1):
        event["seq"] = start + offset
    return events


def _event(kind: str, text: str, *, at: str = "", detail: str = "", tool: str = "", cwd: str = "", subagent: str = "") -> dict:
    return {
        "seq": 0,
        "kind": kind,
        "tool": tool,
        "text": text,
        "detail": detail,
        "at": at,
        "cwd": cwd,
        "subagent": subagent,
    }


def _blocks(row: dict) -> list[dict]:
    message = row.get("message") or {}
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [block for block in content if isinstance(block, dict)]
    return []


def _user_text(raw: str) -> str:
    match = USER_QUERY_RE.search(raw or "")
    text = match.group(1) if match else TAG_RE.sub("", raw or "")
    return _clip(text, TEXT_LIMIT)


def _user_time(raw: str) -> str:
    match = TIMESTAMP_RE.search(raw or "")
    return match.group(1).strip() if match else ""


def _tool_event(block: dict, subagent: str) -> dict:
    name = str(block.get("name") or "tool")
    raw_input = block.get("input")
    payload = raw_input if isinstance(raw_input, dict) else {}
    if name == "Shell":
        return _event(
            "command",
            _clip(str(payload.get("command") or ""), COMMAND_LIMIT),
            detail=_clip(str(payload.get("description") or ""), 240),
            tool="Shell",
            cwd=_clip(str(payload.get("working_directory") or ""), 240),
            subagent=subagent,
        )
    return _event("tool", _tool_summary(name, payload), tool=name, subagent=subagent)


def _tool_summary(name: str, payload: dict) -> str:
    if name in {"Read", "Delete"}:
        return _clip(str(payload.get("path") or name), 300)
    if name == "Glob":
        return _clip(
            f"{payload.get('glob_pattern') or ''}  {payload.get('target_directory') or ''}".strip(),
            300,
        )
    if name == "Grep":
        where = payload.get("path") or payload.get("glob") or ""
        return _clip(f"{payload.get('pattern') or ''}  {where}".strip(), 300)
    if name == "Write":
        return _clip(str(payload.get("path") or "Write"), 300)
    if name == "StrReplace":
        path = str(payload.get("path") or "")
        old = str(payload.get("old_string") or "").strip().splitlines()
        hint = old[0][:80] if old else ""
        return _clip(f"{path}  {hint}".strip(), 300)
    bits = []
    for key, value in list(payload.items())[:4]:
        if key in _LARGE_KEYS or isinstance(value, (dict, list)):
            continue
        bits.append(f"{key}={_clip(str(value), 80)}")
    return _clip(f"{name}: {', '.join(bits)}" if bits else name, 300)


def _iso(mtime: float) -> str:
    return datetime.fromtimestamp(mtime).isoformat(timespec="seconds")
