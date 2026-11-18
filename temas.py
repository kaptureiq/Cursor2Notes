"""Temas visuais do Cursor2Notes, copiados do catálogo do KaptureBOARD.

Os temas ficam em `temas.json`. Cada tema vira um bloco de variáveis CSS
aplicado ao app.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CAMINHO = Path(__file__).with_name("temas.json")
TEMA_PADRAO = "kapture_sap"
GRUPOS = {"oficiais": "Oficiais", "fintech": "Fintech", "geotech": "GeoTech"}
_COR = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\([\d\s.,%]+\))$")
_FONTE = re.compile(r"^[\w\s'\",\-]+$")

ESTILO_COMUM = """
.block-container { padding-top: 1.4rem; max-width: 92rem; }
.ev { margin: 0.7rem 0; padding: 0.7rem 0.85rem; background: var(--c2n-surface); border: 1px solid var(--c2n-border); border-radius: var(--c2n-radius); }
.ev header { display: flex; gap: 0.75rem; align-items: baseline; }
.tag { font-size: 0.75rem; letter-spacing: 0.03em; text-transform: uppercase; color: var(--c2n-primary); }
.ev.comment .tag { color: var(--c2n-text); }
.ev.thinking .tag { color: var(--c2n-muted); }
.ev.thinking p { font-style: italic; color: var(--c2n-muted); }
.ev.tool .tag, .ev.subagent .tag { color: var(--c2n-muted); }
time, .cwd, .detail, .note, .meta { color: var(--c2n-muted); }
.cwd, .detail, time { font-size: 0.85rem; }
pre { white-space: pre-wrap; word-break: break-word; font-family: Consolas, monospace; font-size: 0.9rem; background: var(--c2n-bg); padding: 0.4rem; border-radius: var(--c2n-radius); }
p { margin: 0.3rem 0; white-space: pre-wrap; }
.final { margin: 0.4rem 0 0.8rem; padding: 0.75rem 0.9rem; border-left: 3px solid var(--c2n-primary); background: var(--c2n-surface); border-radius: var(--c2n-radius); }
.final span { display: block; color: var(--c2n-primary); font-size: 0.8rem; }
div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button { text-align: left; white-space: normal; height: auto; border-radius: var(--c2n-radius); }
"""


def carregar(caminho: Path = CAMINHO) -> list[dict]:
    return json.loads(caminho.read_text(encoding="utf-8"))["temas"]


def por_nome(temas: list[dict]) -> dict[str, dict]:
    return {tema["name"]: tema for tema in temas}


def rotulo(tema: dict) -> str:
    return f"{GRUPOS.get(tema['grupo'], tema['grupo'])} · {tema['display_name']}"


def css(tema: dict) -> str:
    tokens = (tema.get("theme_config") or {}).get("tokens") or {}
    cores = tokens.get("colors") or {}
    tipo = tokens.get("typography") or {}

    def cor(chave: str, padrao: str) -> str:
        valor = str(cores.get(chave) or "")
        return valor if _COR.match(valor) else padrao

    fonte = str(tipo.get("font_family") or "")
    fonte = fonte if _FONTE.match(fonte) else "sans-serif"
    raio = str((tema.get("theme_config") or {}).get("radius") or "4px")
    raio = raio if re.match(r"^\d+(\.\d+)?(px|rem)$", raio) else "4px"
    variaveis = {
        "--c2n-bg": cor("background", "#ffffff"),
        "--c2n-surface": cor("surface", "#ffffff"),
        "--c2n-text": cor("text", "#0f172a"),
        "--c2n-muted": cor("text_muted", "#64748b"),
        "--c2n-border": cor("border", "#e2e8f0"),
        "--c2n-primary": cor("primary", "#2563eb"),
        "--c2n-font": fonte,
        "--c2n-radius": raio,
    }
    corpo = "\n".join(f"  {nome}: {valor};" for nome, valor in variaveis.items())
    return f""":root {{
{corpo}
}}
.stApp {{ background: var(--c2n-bg); color: var(--c2n-text); font-family: var(--c2n-font); }}
[data-testid="stSidebar"] {{ background: var(--c2n-surface); }}
button[kind="primary"] {{ background-color: var(--c2n-primary); border-color: var(--c2n-primary); color: #ffffff; }}
.stApp, .stApp h1, .stApp h2, .stApp h3, .stApp h4, [data-testid="stWidgetLabel"] p,
[data-testid="stMarkdownContainer"] p, [data-testid="stRadio"] label p, [data-testid="stCheckbox"] label p,
[data-testid="stCaptionContainer"], [data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ color: var(--c2n-text); }}
input, textarea, [data-baseweb="select"] > div, [data-baseweb="select"] span {{ background-color: var(--c2n-surface) !important; color: var(--c2n-text) !important; }}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary p {{ color: var(--c2n-text) !important; }}
[data-testid="stExpander"], [data-testid="stExpander"] details {{ background-color: var(--c2n-surface) !important; border-color: var(--c2n-border) !important; }}
button:not([kind="primary"]) {{ background-color: var(--c2n-surface) !important; color: var(--c2n-text) !important; border-color: var(--c2n-border) !important; }}
button:not([kind="primary"]) p, button:not([kind="primary"]) span {{ color: var(--c2n-text) !important; }}
button:not([kind="primary"]):hover {{ border-color: var(--c2n-primary) !important; color: var(--c2n-primary) !important; }}
[data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="popover"] ul, [data-baseweb="menu"] ul {{ background-color: var(--c2n-surface) !important; }}
[data-baseweb="popover"] li, [data-baseweb="menu"] li {{ color: var(--c2n-text) !important; }}
"""
