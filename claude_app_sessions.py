"""Consulta somente leitura das conversas do aplicativo Claude.

O aplicativo guarda o cache em %APPDATA%/Claude/IndexedDB. As cópias
grandes ficam em blobs Snappy; as outras ficam nas tabelas e no registro
do LevelDB. O valor é serializado no formato do V8. A leitura não grava
nesse diretório.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from cursor_agent_sessions import (
    COMMAND_LIMIT,
    COMMENT_LIMIT,
    EVENT_LIMIT,
    HEAD_KEEP,
    LIST_COMMANDS,
    TEXT_LIMIT,
    TITLE_LIMIT,
    CursorSessionsError,
    _clip,
    _event,
)
from v8_value import V8Error, decode

ROOT_ENV = "CLAUDE_APP2NOTES_ROOT"
PASTA = "claude"
LABEL = "Claude"
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
ANCORA = b'o"\x10conversationUuid'
MAGIC_LDB = b"\x57\xfb\x80\x8b\x24\x75\x47\xdb"
COMANDOS = frozenset({"Bash", "PowerShell", "Shell"})
RESUMO = ("command", "cmd", "file_path", "path", "pattern", "query", "url", "description", "subject")


def claude_app_root() -> Path:
    raw = os.environ.get(ROOT_ENV, "").strip()
    if raw:
        return Path(raw)
    appdata = os.environ.get("APPDATA", "").strip()
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / "Claude" / "IndexedDB"


def _varint(data: bytes, pos: int) -> tuple[int, int]:
    result = shift = 0
    while pos < len(data) and shift <= 28:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if byte < 0x80:
            return result, pos
        shift += 7
    raise ValueError("varint")


def _copiar(saida: bytearray, offset: int, tamanho: int) -> None:
    if offset <= 0 or offset > len(saida):
        raise ValueError("offset")
    for _ in range(tamanho):
        saida.append(saida[-offset])


def _snappy(data: bytes, inicio: int) -> tuple[bytes, int]:
    tamanho, pos = _varint(data, inicio)
    if tamanho > 32_000_000:
        raise ValueError("grande")
    saida = bytearray()
    while len(saida) < tamanho:
        tag = data[pos]
        pos += 1
        tipo = tag & 3
        if tipo == 0:
            comprimento = tag >> 2
            if comprimento >= 60:
                extra = comprimento - 59
                comprimento = int.from_bytes(data[pos : pos + extra], "little")
                pos += extra
            comprimento += 1
            saida += data[pos : pos + comprimento]
            pos += comprimento
        elif tipo == 1:
            comprimento = ((tag >> 2) & 7) + 4
            deslocamento = ((tag & 0xE0) << 3) | data[pos]
            pos += 1
            _copiar(saida, deslocamento, comprimento)
        elif tipo == 2:
            comprimento = (tag >> 2) + 1
            deslocamento = int.from_bytes(data[pos : pos + 2], "little")
            pos += 2
            _copiar(saida, deslocamento, comprimento)
        else:
            comprimento = (tag >> 2) + 1
            deslocamento = int.from_bytes(data[pos : pos + 4], "little")
            pos += 4
            _copiar(saida, deslocamento, comprimento)
    return bytes(saida), pos


def _plano(data: bytes) -> bytes | None:
    for inicio in range(0, 8):
        try:
            plain, usado = _snappy(data, inicio)
        except (ValueError, IndexError):
            continue
        if usado == len(data) and ANCORA in plain:
            return plain
    if ANCORA in data:
        return data
    return None


def _itens(valor) -> list:
    if isinstance(valor, list):
        return [item for item in valor if item is not None]
    if not isinstance(valor, dict):
        return []
    pares = []
    for chave, item in valor.items():
        if isinstance(chave, int):
            pares.append((chave, item))
        elif isinstance(chave, str) and chave.isdigit():
            pares.append((int(chave), item))
    pares.sort(key=lambda par: par[0])
    return [item for _, item in pares]


def _hora(valor) -> str:
    if isinstance(valor, (int, float)) and valor > 1_000_000_000_000:
        quando = datetime.fromtimestamp(valor / 1000, timezone.utc).astimezone()
        return quando.strftime("%Y-%m-%d %H:%M:%S")
    if not isinstance(valor, str) or not valor:
        return ""
    try:
        quando = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return quando.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _texto_bloco(bloco: dict) -> str:
    texto = bloco.get("text") or bloco.get("thinking") or ""
    if not isinstance(texto, str):
        return ""
    return _clip(texto, TEXT_LIMIT)


def _resumo_ferramenta(nome: str, entrada) -> str:
    if not isinstance(entrada, dict):
        return _clip(nome, 300)
    for campo in RESUMO:
        valor = entrada.get(campo)
        if isinstance(valor, str) and valor.strip():
            return _clip(f"{nome}: {valor.strip()}", 300)
    return _clip(nome, 300)


def _eventos_mensagem(mensagem: dict) -> list[dict]:
    quando = _hora(mensagem.get("created_at"))
    sender = mensagem.get("sender")
    feitos: list[dict] = []
    for bloco in _itens(mensagem.get("content")):
        if not isinstance(bloco, dict):
            continue
        tipo = bloco.get("type")
        if sender == "human" and tipo == "text":
            texto = _texto_bloco(bloco)
            if texto:
                feitos.append(_event("user", texto, at=quando))
        elif sender == "assistant" and tipo == "thinking":
            texto = _texto_bloco(bloco)
            if texto:
                feitos.append(_event("thinking", texto, at=quando, detail=_clip(str(bloco.get("title") or ""), 80)))
        elif sender == "assistant" and tipo == "text":
            texto = _texto_bloco(bloco)
            if texto:
                feitos.append(_event("comment", texto, at=quando))
        elif sender == "assistant" and tipo == "tool_use":
            nome = str(bloco.get("name") or "tool")
            entrada = bloco.get("input") if isinstance(bloco.get("input"), dict) else {}
            if nome in COMANDOS:
                feitos.append(
                    _event(
                        "command",
                        _clip(str(entrada.get("command") or entrada.get("cmd") or ""), COMMAND_LIMIT),
                        detail=_clip(str(entrada.get("description") or ""), 240),
                        tool=nome,
                        at=quando,
                    )
                )
            else:
                feitos.append(_event("tool", _resumo_ferramenta(nome, entrada), tool=nome, at=quando))
    return feitos


def _conversa(valor) -> dict | None:
    if not isinstance(valor, dict):
        return None
    identificador = valor.get("conversationUuid")
    arvore = valor.get("tree")
    if not isinstance(identificador, str) or not isinstance(arvore, dict):
        return None
    if "messages" not in arvore:
        return None
    return valor


def _procurar(valor, achados: list[dict], vistos: set[int], profundidade: int = 0) -> None:
    if profundidade > 12:
        return
    marca = id(valor)
    if marca in vistos:
        return
    vistos.add(marca)
    conversa = _conversa(valor)
    if conversa is not None:
        achados.append(conversa)
        return
    if isinstance(valor, dict):
        for item in valor.values():
            if isinstance(item, (dict, list)):
                _procurar(item, achados, vistos, profundidade + 1)
    elif isinstance(valor, list):
        for item in valor:
            if isinstance(item, (dict, list)):
                _procurar(item, achados, vistos, profundidade + 1)


def _decodificar(data: bytes) -> list[dict]:
    plain = _plano(data)
    if plain is None:
        return []
    return _conversas_valor(plain)


def _conversas_valor(valor: bytes) -> list[dict]:
    inicio = valor.find(ANCORA)
    if inicio < 0:
        return []
    try:
        item, _ = decode(valor, inicio)
    except V8Error:
        return []
    achados: list[dict] = []
    _procurar(item, achados, set())
    return achados


def _bloco(data: bytes, offset: int, tamanho: int) -> bytes:
    if tamanho <= 0 or offset < 0 or offset + tamanho > len(data):
        return b""
    fatia = data[offset : offset + tamanho]
    try:
        plain, usado = _snappy(fatia, 0)
    except (ValueError, IndexError):
        return fatia
    if usado == len(fatia) and len(plain) >= 4:
        return plain
    return fatia


def _entradas(conteudo: bytes) -> list[tuple[bytes, bytes]]:
    if len(conteudo) < 4:
        return []
    quantidade = int.from_bytes(conteudo[-4:], "little")
    if quantidade <= 0 or quantidade > 100_000 or 4 * quantidade + 4 > len(conteudo):
        return []
    base = len(conteudo) - 4 - 4 * quantidade
    reinicios = [
        int.from_bytes(conteudo[base + 4 * i : base + 4 * i + 4], "little") for i in range(quantidade)
    ]
    if any(ponto > base for ponto in reinicios):
        return []
    itens: list[tuple[bytes, bytes]] = []
    chave = b""
    for inicio in reinicios:
        pos = inicio
        while pos < base:
            try:
                compartilhado, pos = _varint(conteudo, pos)
                exclusivo, pos = _varint(conteudo, pos)
                valor_tam, pos = _varint(conteudo, pos)
            except ValueError:
                break
            if compartilhado > len(chave) or pos + exclusivo + valor_tam > base:
                break
            delta = conteudo[pos : pos + exclusivo]
            pos += exclusivo
            valor = conteudo[pos : pos + valor_tam]
            pos += valor_tam
            chave = chave[:compartilhado] + delta
            itens.append((chave, valor))
    return itens


def _tabela(data: bytes) -> list[tuple[bytes, bytes]]:
    if len(data) < 48 or data[-8:] != MAGIC_LDB:
        return []
    pos = len(data) - 48
    try:
        _, pos = _varint(data, pos)
        _, pos = _varint(data, pos)
        index_off, pos = _varint(data, pos)
        index_size, _ = _varint(data, pos)
        indice = _entradas(_bloco(data, index_off, index_size))
    except (ValueError, IndexError):
        return []
    pares: list[tuple[bytes, bytes]] = []
    for _chave, handle in indice:
        try:
            off, cursor = _varint(handle, 0)
            size, _ = _varint(handle, cursor)
        except ValueError:
            continue
        pares.extend(_entradas(_bloco(data, off, size)))
    return pares


def _lote(atual: bytes, saida: list[tuple[bytes, bytes]]) -> None:
    if len(atual) < 12:
        return
    quantidade = int.from_bytes(atual[8:12], "little")
    cursor = 12
    for _ in range(quantidade):
        if cursor >= len(atual):
            return
        tipo = atual[cursor]
        cursor += 1
        try:
            klen, cursor = _varint(atual, cursor)
        except ValueError:
            return
        if cursor + klen > len(atual):
            return
        chave = atual[cursor : cursor + klen]
        cursor += klen
        if tipo == 0:
            continue
        try:
            vlen, cursor = _varint(atual, cursor)
        except ValueError:
            return
        if cursor + vlen > len(atual):
            return
        saida.append((chave, atual[cursor : cursor + vlen]))
        cursor += vlen


def _log(data: bytes) -> list[tuple[bytes, bytes]]:
    saida: list[tuple[bytes, bytes]] = []
    pendente = bytearray()
    for base in range(0, len(data), 32768):
        pos = base
        fim = min(base + 32768, len(data))
        while pos + 7 <= fim:
            tamanho = int.from_bytes(data[pos + 4 : pos + 6], "little")
            tipo = data[pos + 6]
            pos += 7
            if tamanho == 0 or pos + tamanho > fim:
                break
            fragmento = data[pos : pos + tamanho]
            pos += tamanho
            if tipo == 1:
                _lote(fragmento, saida)
                pendente.clear()
            elif tipo == 2:
                pendente = bytearray(fragmento)
            elif tipo == 3 and pendente:
                pendente.extend(fragmento)
            elif tipo == 4 and pendente:
                pendente.extend(fragmento)
                _lote(bytes(pendente), saida)
                pendente.clear()
            else:
                pendente.clear()
    return saida


def _uuid_na_chave(chave: bytes) -> str:
    pos = chave.find(b"\x01\x24")
    if pos < 0 or pos + 74 > len(chave):
        return ""
    texto = chave[pos + 2 : pos + 74].decode("utf-16le", errors="ignore")
    return texto if UUID_RE.match(texto) else ""


def _arquivos(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    ignorar = {"LOCK", "CURRENT", "LOG", "LOG.old"}
    return sorted(
        caminho
        for caminho in root.rglob("*")
        if caminho.is_file() and caminho.name not in ignorar and not caminho.name.startswith("MANIFEST")
    )


def _guardar(por_id: dict[str, dict], conversa: dict) -> None:
    identificador = str(conversa.get("conversationUuid") or "")
    if not UUID_RE.match(identificador):
        return
    atual = por_id.get(identificador)
    if atual is None or _mensagens(conversa) >= _mensagens(atual):
        por_id[identificador] = conversa


def _carregar(root: Path) -> list[dict]:
    por_id: dict[str, dict] = {}
    maiores: dict[str, bytes] = {}
    for caminho in _arquivos(root):
        try:
            dados = caminho.read_bytes()
        except OSError:
            continue
        if len(dados) >= 8 and dados[-8:] == MAGIC_LDB:
            pares = _tabela(dados)
        elif caminho.suffix == ".log":
            pares = _log(dados)
        else:
            for conversa in _decodificar(dados):
                _guardar(por_id, conversa)
            continue
        for chave, valor in pares:
            if ANCORA not in valor:
                continue
            identificador = _uuid_na_chave(chave)
            if not identificador:
                for conversa in _conversas_valor(valor):
                    _guardar(por_id, conversa)
                continue
            atual = maiores.get(identificador)
            if atual is None or len(valor) > len(atual):
                maiores[identificador] = valor
    for valor in maiores.values():
        for conversa in _conversas_valor(valor):
            _guardar(por_id, conversa)
    return list(por_id.values())


def _mensagens(conversa: dict) -> int:
    arvore = conversa.get("tree") if isinstance(conversa.get("tree"), dict) else {}
    return len(_itens(arvore.get("messages")))


def _eventos(conversa: dict) -> list[dict]:
    arvore = conversa.get("tree") if isinstance(conversa.get("tree"), dict) else {}
    eventos: list[dict] = []
    for mensagem in _itens(arvore.get("messages")):
        if isinstance(mensagem, dict):
            eventos.extend(_eventos_mensagem(mensagem))
    return eventos


def _titulo(eventos: list[dict]) -> str:
    for evento in eventos:
        if evento["kind"] == "user" and evento["text"]:
            return _clip(evento["text"].splitlines()[0], TITLE_LIMIT)
    return "(sem pedido)"


def _resumo(conversa: dict, eventos: list[dict]) -> dict:
    titulo = _titulo(eventos)
    inicio = ""
    ultimo = ""
    usuarios = comentarios = comandos = 0
    previa: list[str] = []
    for evento in eventos:
        tipo = evento["kind"]
        if tipo == "user":
            usuarios += 1
            if not inicio:
                inicio = evento.get("at") or ""
        elif tipo == "comment" and evento["text"]:
            comentarios += 1
            ultimo = evento["text"]
        elif tipo == "command":
            comandos += 1
            if len(previa) < LIST_COMMANDS and evento["text"]:
                previa.append(_clip(evento["text"].splitlines()[0], 180))
    atualizado = ""
    for mensagem in reversed(_itens((conversa.get("tree") or {}).get("messages"))):
        if isinstance(mensagem, dict):
            atualizado = _hora(mensagem.get("updated_at") or mensagem.get("created_at"))
            if atualizado:
                break
    if not atualizado:
        atualizado = _hora(conversa.get("conversationUpdatedAt") or conversa.get("writtenAt"))
    return {
        "id": conversa.get("conversationUuid"),
        "title": titulo,
        "started_at": inicio,
        "updated_at": atualizado,
        "user_turns": usuarios,
        "comments": comentarios,
        "commands": comandos,
        "last_comment": _clip(ultimo, COMMENT_LIMIT),
        "command_preview": previa,
        "subagents": 0,
    }


def _checar_pasta(slug: str) -> None:
    if slug != PASTA:
        raise CursorSessionsError("Pasta inválida.", 400)


def list_folders(*, include_temporary: bool = False, root: Path | None = None) -> dict:
    del include_temporary
    base = root or claude_app_root()
    conversas = _carregar(base)
    payload = {"root": str(base), "folders": [], "note": ""}
    if not conversas:
        payload["note"] = "Nenhuma conversa do aplicativo Claude encontrada neste computador."
        return payload
    atualizados = [item for item in (_resumo(conversa, _eventos(conversa))["updated_at"] for conversa in conversas) if item]
    payload["folders"] = [
        {
            "slug": PASTA,
            "label": LABEL,
            "path": None,
            "kind": "workspace",
            "sessions": len(conversas),
            "updated_at": max(atualizados) if atualizados else "",
        }
    ]
    return payload


def list_sessions(slug: str, root: Path | None = None) -> dict:
    _checar_pasta(slug)
    sessoes = [_resumo(conversa, _eventos(conversa)) for conversa in _carregar(root or claude_app_root())]
    sessoes.sort(key=lambda item: item["updated_at"] or "", reverse=True)
    return {
        "folder": {"slug": PASTA, "label": LABEL, "path": None, "kind": "workspace"},
        "sessions": sessoes,
    }


def _limitar(eventos: list[dict], full: bool) -> tuple[list[dict], bool, int]:
    if full or len(eventos) <= EVENT_LIMIT:
        return eventos, False, 0
    omitidos = len(eventos) - EVENT_LIMIT
    return eventos[:HEAD_KEEP] + eventos[-(EVENT_LIMIT - HEAD_KEEP) :], True, omitidos


def session_detail(slug: str, session_id: str, root: Path | None = None, *, full: bool = False) -> dict:
    if not UUID_RE.match(session_id or ""):
        raise CursorSessionsError("Conversa inválida.", 400)
    _checar_pasta(slug)
    alvo = next(
        (
            conversa
            for conversa in _carregar(root or claude_app_root())
            if str(conversa.get("conversationUuid") or "").lower() == session_id.lower()
        ),
        None,
    )
    if alvo is None:
        raise CursorSessionsError("Conversa não encontrada.", 404)
    eventos, truncado, omitidos = _limitar(_eventos(alvo), full)
    for indice, evento in enumerate(eventos, start=1):
        evento["seq"] = indice
    resumo = _resumo(alvo, _eventos(alvo))
    resumo["truncated"] = truncado
    resumo["omitted"] = omitidos
    return {"session": resumo, "events": eventos}
