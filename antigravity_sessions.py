"""Consulta somente leitura das conversas do Google Antigravity.

As transcrições ficam em <appData>/brain/<id>/.system_generated/logs/transcript_full.jsonl
(ou transcript.jsonl). O resumo das conversas e seus workspaces fica em
<appData>/conversation_summaries.db.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request
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

ROOT_ENV = "ANTIGRAVITY2NOTES_ROOT"
USER_REQUEST_RE = re.compile(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", re.DOTALL)
CLEAN_TAGS_RE = re.compile(
    r"<(?:ADDITIONAL_METADATA|USER_SETTINGS_CHANGE|system|identity)[^>]*>.*?</(?:ADDITIONAL_METADATA|USER_SETTINGS_CHANGE|system|identity)>",
    re.DOTALL | re.IGNORECASE,
)
RESUMO_CAMPOS = (
    "Path",
    "path",
    "file_path",
    "query",
    "queries",
    "toolSummary",
    "Description",
    "description",
    "Prompt",
    "prompt",
    "Message",
    "message",
    "CommandLine",
    "command",
    "Action",
    "action",
    "TypeName",
    "Role",
    "url",
    "pattern",
)


def antigravity_root() -> Path:
    raw = os.environ.get(ROOT_ENV, "").strip()
    if raw:
        return Path(raw)
    return Path.home() / ".gemini" / "antigravity"


def _resolver_caminhos(root: Path | None = None) -> tuple[Path, Path | None]:
    base = (root or antigravity_root()).resolve()
    if (base / "brain").is_dir():
        brain = base / "brain"
        db = base / "conversation_summaries.db"
        return brain, db if db.is_file() else None
    if base.name == "brain":
        db = base.parent / "conversation_summaries.db"
        return base, db if db.is_file() else None
    db = base / "conversation_summaries.db"
    return base, db if db.is_file() else None


def _caminho_transcricao(brain: Path, session_id: str) -> Path | None:
    pasta = brain / session_id
    if pasta.is_dir():
        candidatos = (
            pasta / ".system_generated" / "logs" / "transcript_full.jsonl",
            pasta / ".system_generated" / "logs" / "transcript.jsonl",
            pasta / f"{session_id}.jsonl",
            pasta / "transcript.jsonl",
        )
        for cand in candidatos:
            if cand.is_file():
                return cand
    cand_direto = brain / f"{session_id}.jsonl"
    if cand_direto.is_file():
        return cand_direto
    return None


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


def _uri_para_caminho(uri: str) -> str:
    if not uri:
        return ""
    try:
        parsed = urllib.parse.urlparse(uri)
        if parsed.scheme == "file":
            return urllib.request.url2pathname(urllib.parse.unquote(parsed.path))
    except Exception:
        pass
    return uri


def _slug(rotulo: str, usados: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", rotulo).strip("-")[:160] or "antigravity"
    slug = base
    numero = 2
    while slug in usados:
        slug = f"{base}-{numero}"[:180]
        numero += 1
    usados.add(slug)
    return slug


def folder_kind(slug: str) -> str:
    low = slug.lower()
    if "temp" in low or "worktree" in low:
        return "temporary"
    return "workspace"


def _resumo_ferramenta(nome: str, args: dict) -> str:
    for campo in RESUMO_CAMPOS:
        valor = args.get(campo)
        if isinstance(valor, str) and valor.strip():
            return _clip(f"{nome}: {valor.strip()}", 300)
        if isinstance(valor, list) and valor:
            itens = ", ".join(str(x) for x in valor)
            return _clip(f"{nome}: {itens}", 300)
    return _clip(nome, 300)


def _parse_transcript(path: Path, subagent: str = "") -> tuple[list[dict], str]:
    events: list[dict] = []
    primeiro_pedido = ""
    try:
        handle = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return events, primeiro_pedido
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

            tipo = row.get("type")
            source = row.get("source")
            at = _hora(row.get("created_at"))

            if tipo == "USER_INPUT" or source == "USER_EXPLICIT":
                raw = str(row.get("content") or "")
                match = USER_REQUEST_RE.search(raw)
                if match:
                    texto = match.group(1).strip()
                else:
                    texto = CLEAN_TAGS_RE.sub("", raw).strip()
                texto = _clip(texto, TEXT_LIMIT)
                if texto:
                    if not primeiro_pedido:
                        primeiro_pedido = texto
                    events.append(
                        _event("user", texto, at=at, subagent=subagent)
                    )
            elif tipo == "PLANNER_RESPONSE":
                th = row.get("thinking")
                if th and isinstance(th, str) and th.strip():
                    events.append(
                        _event("thinking", _clip(th.strip(), TEXT_LIMIT), at=at, subagent=subagent)
                    )
                cnt = row.get("content")
                if cnt and isinstance(cnt, str) and cnt.strip():
                    events.append(
                        _event("comment", _clip(cnt.strip(), TEXT_LIMIT), at=at, subagent=subagent)
                    )
                tool_calls = row.get("tool_calls")
                if isinstance(tool_calls, list):
                    for tc in tool_calls:
                        if not isinstance(tc, dict):
                            continue
                        name = str(tc.get("name") or "tool")
                        args = tc.get("args") or {}
                        if not isinstance(args, dict):
                            args = {}
                        if name == "run_command":
                            cmd = str(args.get("CommandLine") or "").strip()
                            summary = str(args.get("toolSummary") or "").strip()
                            cwd = str(args.get("Cwd") or "").strip()
                            events.append(
                                _event(
                                    "command",
                                    _clip(cmd, COMMAND_LIMIT),
                                    detail=_clip(summary, 240),
                                    tool=name,
                                    cwd=cwd,
                                    at=at,
                                    subagent=subagent,
                                )
                            )
                        elif name == "invoke_subagent":
                            role = str(args.get("Role") or args.get("TypeName") or "Agente auxiliar").strip()
                            prompt = str(args.get("Prompt") or "").strip()
                            events.append(
                                _event(
                                    "subagent",
                                    _clip(prompt, TEXT_LIMIT),
                                    detail=_clip(role, 240),
                                    tool=name,
                                    at=at,
                                    subagent=subagent,
                                )
                            )
                        else:
                            detail = _resumo_ferramenta(name, args)
                            events.append(
                                _event("tool", detail, tool=name, at=at, subagent=subagent)
                            )
    return events, primeiro_pedido


def _subagentes_em_disco(brain: Path, session_id: str) -> list[str]:
    pasta = brain / session_id / "subagents"
    if not pasta.is_dir():
        return []
    encontrados = []
    try:
        for item in pasta.iterdir():
            if item.is_file() and item.suffix == ".jsonl" and SESSION_RE.match(item.stem):
                encontrados.append(item.stem)
            elif item.is_dir() and SESSION_RE.match(item.name):
                encontrados.append(item.name)
    except OSError:
        pass
    return sorted(encontrados)


def _carregar_banco(db_path: Path) -> tuple[dict[str, dict], dict[str, list[str]]]:
    """Lê conversation_summaries.db e devolve metadados e mapa de subagentes por pai."""
    info_sessoes: dict[str, dict] = {}
    subagentes: dict[str, list[str]] = {}
    uri = "file:" + db_path.resolve().as_posix() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=1)
    except sqlite3.Error:
        return info_sessoes, subagentes
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        cursor = conn.execute(
            """
            SELECT conversation_id, title, preview, step_count,
                   last_modified_time, workspace_uris, parent_conversation_id
            FROM conversation_summaries
            """
        )
        for row in cursor:
            cid = str(row["conversation_id"] or "").strip()
            if not cid or not SESSION_RE.match(cid):
                continue
            parent = str(row["parent_conversation_id"] or "").strip()
            if parent:
                subagentes.setdefault(parent, []).append(cid)
            info_sessoes[cid] = {
                "id": cid,
                "title": str(row["title"] or "").strip(),
                "preview": str(row["preview"] or "").strip(),
                "step_count": int(row["step_count"] or 0),
                "last_modified_time": str(row["last_modified_time"] or "").strip(),
                "workspace_uris": str(row["workspace_uris"] or "").strip(),
                "parent": parent,
            }
    except sqlite3.Error:
        pass
    finally:
        conn.close()
    return info_sessoes, subagentes


def _carregar_sessoes(root: Path | None = None) -> list[dict]:
    brain, db_path = _resolver_caminhos(root)
    if not brain.is_dir():
        return []

    info_db: dict[str, dict] = {}
    subagentes_db: dict[str, list[str]] = {}
    if db_path and db_path.is_file():
        info_db, subagentes_db = _carregar_banco(db_path)

    # Identifica todas as sessões com transcrição em brain
    candidatos_ids: set[str] = set()
    try:
        for entrada in brain.iterdir():
            if entrada.is_dir() and SESSION_RE.match(entrada.name):
                candidatos_ids.add(entrada.name)
            elif entrada.is_file() and entrada.suffix == ".jsonl" and SESSION_RE.match(entrada.stem):
                candidatos_ids.add(entrada.stem)
    except OSError:
        return []

    # Também inclui sessões conhecidas no DB se o arquivo existir
    for cid in info_db:
        if _caminho_transcricao(brain, cid) is not None:
            candidatos_ids.add(cid)

    # Agrupa por pasta (workspace)
    sessoes: list[dict] = []
    usados: set[str] = set()
    grupos_slugs: dict[str, str] = {}

    for cid in sorted(candidatos_ids):
        db_meta = info_db.get(cid, {})
        parent = db_meta.get("parent", "")
        # Subagentes não são listados como sessões principais
        if parent and parent in candidatos_ids:
            continue

        trans_path = _caminho_transcricao(brain, cid)
        if not trans_path:
            continue

        rotulo_pasta = ""
        caminho_pasta = None
        workspace_raw = db_meta.get("workspace_uris", "")
        if workspace_raw:
            try:
                uris = json.loads(workspace_raw)
                if isinstance(uris, list) and uris:
                    caminho_pasta = _uri_para_caminho(str(uris[0]))
                    rotulo_pasta = caminho_pasta
            except Exception:
                pass

        if not rotulo_pasta:
            rotulo_pasta = "Antigravity"
            caminho_pasta = None

        if rotulo_pasta not in grupos_slugs:
            grupos_slugs[rotulo_pasta] = _slug(rotulo_pasta, usados)

        subs = list(subagentes_db.get(cid, []))
        for disco_sub in _subagentes_em_disco(brain, cid):
            if disco_sub not in subs:
                subs.append(disco_sub)

        mtime = trans_path.stat().st_mtime
        updated = _hora(db_meta.get("last_modified_time")) or _iso(mtime)

        sessoes.append(
            {
                "id": cid,
                "slug": grupos_slugs[rotulo_pasta],
                "label": rotulo_pasta,
                "path": caminho_pasta,
                "db_title": db_meta.get("title") or "",
                "transcript_path": trans_path,
                "subagents": subs,
                "updated_at": updated,
            }
        )

    return sessoes


def _resumo_sessao(item: dict) -> dict:
    events, primeiro_pedido = _parse_transcript(item["transcript_path"])
    title = item.get("db_title") or primeiro_pedido or "(sem pedido)"
    started = ""
    last_comment = ""
    users = comments = commands = 0
    command_preview: list[str] = []

    for event in events:
        k = event["kind"]
        if k == "user":
            users += 1
            if not started:
                started = event.get("at") or ""
            if not title and event["text"]:
                title = event["text"].splitlines()[0]
        elif k == "comment" and event["text"]:
            comments += 1
            last_comment = event["text"]
        elif k == "command":
            commands += 1
            if len(command_preview) < LIST_COMMANDS and event["text"]:
                command_preview.append(_clip(event["text"].splitlines()[0], 180))

    return {
        "id": item["id"],
        "title": _clip(title, TITLE_LIMIT),
        "started_at": started,
        "updated_at": item["updated_at"],
        "user_turns": users,
        "comments": comments,
        "commands": commands,
        "last_comment": _clip(last_comment, COMMENT_LIMIT),
        "command_preview": command_preview,
        "subagents": len(item.get("subagents") or []),
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
                "kind": folder_kind(sessao["slug"]),
                "sessions": 0,
                "updated_at": "",
            },
        )
        pasta["sessions"] += 1
        if (sessao["updated_at"] or "") > (pasta["updated_at"] or ""):
            pasta["updated_at"] = sessao["updated_at"]
    return sorted(grupos.values(), key=lambda p: p["updated_at"] or "", reverse=True)


def list_folders(*, include_temporary: bool = False, root: Path | None = None) -> dict:
    brain, _ = _resolver_caminhos(root)
    payload = {"root": str(brain), "folders": [], "note": ""}
    if not brain.is_dir():
        payload["note"] = "Nenhuma conversa do Antigravity encontrada neste computador."
        return payload
    sessoes = _carregar_sessoes(root)
    if not sessoes:
        payload["note"] = "Nenhuma conversa do Antigravity encontrada neste computador."
        return payload
    pastas = _pastas(sessoes)
    if not include_temporary:
        pastas = [p for p in pastas if p["kind"] != "temporary"]
    payload["folders"] = pastas
    return payload


def list_sessions(slug: str, root: Path | None = None) -> dict:
    if not SLUG_RE.match(slug or ""):
        raise CursorSessionsError("Pasta inválida.", 400)
    todas = _carregar_sessoes(root)
    sessoes = [item for item in todas if item["slug"] == slug]
    if not sessoes:
        raise CursorSessionsError("Pasta não encontrada.", 404)
    lista = [_resumo_sessao(item) for item in sessoes]
    lista.sort(key=lambda item: item["updated_at"] or "", reverse=True)
    return {
        "folder": {
            "slug": slug,
            "label": sessoes[0]["label"],
            "path": sessoes[0]["path"],
            "kind": folder_kind(slug),
        },
        "sessions": lista,
    }


def _limitar(eventos: list[dict], full: bool) -> tuple[list[dict], bool, int]:
    if full or len(eventos) <= EVENT_LIMIT:
        return eventos, False, 0
    omitidos = len(eventos) - EVENT_LIMIT
    return eventos[:HEAD_KEEP] + eventos[-(EVENT_LIMIT - HEAD_KEEP) :], True, omitidos


def session_detail(slug: str, session_id: str, root: Path | None = None, *, full: bool = False) -> dict:
    if not SLUG_RE.match(slug or ""):
        raise CursorSessionsError("Pasta inválida.", 400)
    if not SESSION_RE.match(session_id or ""):
        raise CursorSessionsError("Conversa inválida.", 400)
    todas = _carregar_sessoes(root)
    alvo = next(
        (
            item
            for item in todas
            if item["slug"] == slug and item["id"].lower() == session_id.lower()
        ),
        None,
    )
    if alvo is None:
        raise CursorSessionsError("Conversa não encontrada.", 404)

    brain, _ = _resolver_caminhos(root)
    events, _ = _parse_transcript(alvo["transcript_path"])

    # Inclui eventos dos subagentes
    for sub_id in alvo.get("subagents", []):
        sub_path = _caminho_transcricao(brain, sub_id)
        if sub_path:
            events.append(
                _event(
                    "subagent",
                    sub_id,
                    detail="Agente auxiliar desta tela",
                    tool="subagent",
                )
            )
            sub_events, _ = _parse_transcript(sub_path, subagent=sub_id)
            events.extend(sub_events)

    eventos, truncado, omitidos = _limitar(events, full)
    for indice, evento in enumerate(eventos, start=1):
        evento["seq"] = indice

    resumo = _resumo_sessao(alvo)
    resumo["truncated"] = truncado
    resumo["omitted"] = omitidos
    return {"session": resumo, "events": eventos}
