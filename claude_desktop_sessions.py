"""Consulta somente leitura das sessões do Claude Desktop (modo agente / Cowork).

Cada sessão fica em <conta>/<organização>/local_<id>/audit.jsonl, com mensagens
user e assistant no mesmo formato de transcrição do Claude Code. O app mostra
todas as sessões como uma única pasta.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from claude_code_sessions import _events_for, _parse, _resumo
from cursor_agent_sessions import EVENT_LIMIT, CursorSessionsError, _iso

ROOT_ENV = "CLAUDE_DESKTOP2NOTES_ROOT"
PASTA = "cowork"
LABEL = "Claude Desktop · Cowork"
PREFIXO = "local_"
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def desktop_root() -> Path:
    raw = os.environ.get(ROOT_ENV, "").strip()
    if raw:
        return Path(raw)
    appdata = os.environ.get("APPDATA", "").strip()
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / "Claude" / "local-agent-mode-sessions"


def _arquivos(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    encontrados = [
        p
        for p in root.rglob("audit.jsonl")
        if p.parent.name.startswith(PREFIXO) and UUID_RE.match(p.parent.name[len(PREFIXO):])
    ]
    return sorted(encontrados)


def _sid(path: Path) -> str:
    return path.parent.name[len(PREFIXO):]


def _resumo_sessao(path: Path) -> dict:
    events, titulo = _parse(path)
    resumo = _resumo(path, events, titulo)
    resumo["id"] = _sid(path)
    resumo["subagents"] = 0
    return resumo


def _checar_pasta(slug: str) -> None:
    if slug != PASTA:
        raise CursorSessionsError("Pasta inválida.", 400)


def list_folders(*, include_temporary: bool = False, root: Path | None = None) -> dict:
    base = root or desktop_root()
    arquivos = _arquivos(base)
    payload = {"root": str(base), "folders": [], "note": ""}
    if not arquivos:
        payload["note"] = "Nenhuma conversa do Claude Desktop (Cowork) encontrada neste computador."
        return payload
    payload["folders"] = [
        {
            "slug": PASTA,
            "label": LABEL,
            "path": None,
            "kind": "workspace",
            "sessions": len(arquivos),
            "updated_at": _iso(max(p.stat().st_mtime for p in arquivos)),
        }
    ]
    return payload


def list_sessions(slug: str, root: Path | None = None) -> dict:
    _checar_pasta(slug)
    sessoes = [_resumo_sessao(p) for p in _arquivos(root or desktop_root())]
    sessoes.sort(key=lambda item: item["updated_at"] or "", reverse=True)
    return {
        "folder": {"slug": PASTA, "label": LABEL, "path": None, "kind": "workspace"},
        "sessions": sessoes,
    }


def session_detail(slug: str, session_id: str, root: Path | None = None, *, full: bool = False) -> dict:
    if not UUID_RE.match(session_id or ""):
        raise CursorSessionsError("Conversa inválida.", 400)
    _checar_pasta(slug)
    alvo = next((p for p in _arquivos(root or desktop_root()) if _sid(p).lower() == session_id.lower()), None)
    if alvo is None:
        raise CursorSessionsError("Conversa não encontrada.", 404)
    events, truncated, omitted = _events_for(alvo, limit=None if full else EVENT_LIMIT)
    for index, event in enumerate(events, start=1):
        event["seq"] = index
    resumo = _resumo_sessao(alvo)
    resumo["truncated"] = truncated
    resumo["omitted"] = omitted
    return {"session": resumo, "events": events}
