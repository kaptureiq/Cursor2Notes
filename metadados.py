"""Tags, favoritos e registro de exportações, guardados em `metadados.json`.

O arquivo fica ao lado do app. As conversas de origem nunca são alteradas.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

CAMINHO = Path(__file__).with_name("metadados.json")


class MetadadosError(Exception):
    pass


def chave(slug: str, session_id: str) -> str:
    return f"{slug}|{session_id}"


def carregar(caminho: Path = CAMINHO) -> dict:
    if not caminho.is_file():
        return {"conversas": {}}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise MetadadosError(f"Não consegui ler {caminho.name}: {erro}") from erro
    if not isinstance(dados, dict):
        raise MetadadosError(f"{caminho.name} deve conter um objeto JSON.")
    dados.setdefault("conversas", {})
    return dados


def salvar(dados: dict, caminho: Path = CAMINHO) -> None:
    temporario = caminho.with_suffix(".json.tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporario, caminho)


def obter(dados: dict, key: str) -> dict:
    registro = dados["conversas"].get(key) or {}
    return {
        "tags": list(registro.get("tags") or []),
        "favorita": bool(registro.get("favorita")),
        "exportadas": dict(registro.get("exportadas") or {}),
    }


def _gravar(dados: dict, key: str, registro: dict) -> None:
    dados["conversas"][key] = registro


def definir_tags(dados: dict, key: str, texto: str) -> list[str]:
    """Aceita tags separadas por vírgula. Normaliza para minúsculas com hífens."""
    tags: list[str] = []
    for bruto in texto.split(","):
        tag = re.sub(r"\s+", "-", bruto.strip().lower().lstrip("#"))
        if tag and tag not in tags:
            tags.append(tag)
    registro = obter(dados, key)
    registro["tags"] = tags
    _gravar(dados, key, registro)
    return tags


def alternar_favorita(dados: dict, key: str) -> bool:
    registro = obter(dados, key)
    registro["favorita"] = not registro["favorita"]
    _gravar(dados, key, registro)
    return registro["favorita"]


def registrar_exportacao(dados: dict, key: str, fmt: str, atualizada_em: str) -> None:
    registro = obter(dados, key)
    registro["exportadas"][fmt] = atualizada_em
    _gravar(dados, key, registro)


def precisa_exportar(dados: dict, key: str, fmt: str, atualizada_em: str) -> bool:
    """True se a conversa mudou desde a última exportação neste formato."""
    return obter(dados, key)["exportadas"].get(fmt) != atualizada_em
