"""Mascara segredos (senhas, tokens, strings de conexão) antes da exportação.

Os padrões embutidos ficam aqui. Regras próprias e desativações ficam em
`redacao.json`, ao lado deste arquivo.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("redacao.json")
MARCA = "[REDIGIDO]"

# (nome, padrão, substituição). Os grupos que a substituição referencia
# (\1, \2) são preservados; só o valor secreto é trocado pela marca.
PADROES_EMBUTIDOS = (
    (
        "url-com-senha",
        r"([a-z][a-z0-9+.\-]*://[^\s:/@'\"]+:)[^\s@'\"]+(@)",
        r"\1" + MARCA + r"\2",
    ),
    (
        "oracle-usuario-senha",
        r"\b([A-Za-z_][\w$#]*)/([^\s/@'\"]{1,128})@(?=\S)",
        r"\1/" + MARCA + "@",
    ),
    (
        "atribuicao-sensivel",
        r"(?i)(\b[\w.-]*(?:password|passwd|pwd|senha|secret|segredo|token|api[_-]?key|access[_-]?key|client[_-]?secret)\b[\"']?\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s\"',;]+)",
        r"\1" + MARCA,
    ),
    (
        "argumento-sensivel",
        r"(?i)(--?(?:password|passwd|pwd|pass|token|secret|senha)(?:=|\s+))(\"[^\"]*\"|'[^']*'|[^\s\"']+)",
        r"\1" + MARCA,
    ),
    (
        "bearer",
        r"(?i)(\bbearer\s+)[A-Za-z0-9\-._~+/]{8,}=*",
        r"\1" + MARCA,
    ),
    (
        "chave-aws",
        r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
        MARCA,
    ),
    (
        "token-github",
        r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b",
        MARCA,
    ),
    (
        "token-openai",
        r"\bsk-[A-Za-z0-9_\-]{20,}\b",
        MARCA,
    ),
    (
        "chave-privada",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
        MARCA,
    ),
)


class RedacaoError(Exception):
    pass


def load_rules(path: Path = CONFIG_PATH) -> list[tuple[str, re.Pattern, str]]:
    """Devolve as regras ativas: embutidas menos as desativadas, mais as próprias."""
    config = _read_config(path)
    desativadas = set(config.get("desativar") or [])
    regras = []
    for nome, padrao, substituicao in PADROES_EMBUTIDOS:
        if nome not in desativadas:
            regras.append((nome, _compile(nome, padrao), substituicao))
    for item in config.get("regras") or []:
        nome = str(item.get("nome") or "regra-própria")
        padrao = str(item.get("padrao") or "")
        if not padrao:
            raise RedacaoError(f"Regra '{nome}' sem 'padrao' em redacao.json.")
        regras.append((nome, _compile(nome, padrao), str(item.get("substituicao") or MARCA)))
    return regras


def redact_text(text: str, rules: list[tuple[str, re.Pattern, str]]) -> str:
    for _, padrao, substituicao in rules:
        text = padrao.sub(substituicao, text)
    return text


def redact_detail(detail: dict, rules: list[tuple[str, re.Pattern, str]]) -> dict:
    """Cópia do detalhe da conversa com os textos mascarados."""
    limpo = copy.deepcopy(detail)
    session = limpo.get("session") or {}
    for campo in ("title", "last_comment"):
        if session.get(campo):
            session[campo] = redact_text(str(session[campo]), rules)
    for evento in limpo.get("events") or []:
        for campo in ("text", "detail", "cwd"):
            if evento.get(campo):
                evento[campo] = redact_text(str(evento[campo]), rules)
    return limpo


def _read_config(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise RedacaoError(f"Não consegui ler {path.name}: {erro}") from erro
    if not isinstance(dados, dict):
        raise RedacaoError(f"{path.name} deve conter um objeto JSON.")
    return dados


def _compile(nome: str, padrao: str) -> re.Pattern:
    try:
        return re.compile(padrao)
    except re.error as erro:
        raise RedacaoError(f"Padrão inválido na regra '{nome}': {erro}") from erro
