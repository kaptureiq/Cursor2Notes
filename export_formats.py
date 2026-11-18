"""Exporta uma conversa do Cursor para HTML, Markdown ou PDF."""
from __future__ import annotations

import html
import json
import logging
import re
from pathlib import Path

import redacao

CONFIG_PDF = Path(__file__).with_name("export.json")

logging.getLogger("fontTools").setLevel(logging.ERROR)

LABELS = {
    "user": "Pedido",
    "comment": "Comentário",
    "command": "Comando",
    "tool": "Ferramenta",
    "subagent": "Agente auxiliar",
    "thinking": "Pensamento",
}

_INVALID_NAME = re.compile(r'[\\/:*?"<>|]+')
_FONT_CANDIDATES = (
    (
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf"),
        Path(r"C:\Windows\Fonts\consola.ttf"),
    ),
    (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    ),
)


class ExportError(Exception):
    pass


def kind_label(event: dict) -> str:
    if event.get("kind") == "tool" and event.get("tool"):
        return str(event["tool"])
    return LABELS.get(event.get("kind") or "", str(event.get("kind") or "Evento"))


def file_stem(title: str, session_id: str) -> str:
    cleaned = _INVALID_NAME.sub("-", title or "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip(" .-")[:80] or "conversa"
    short = (session_id or "sessao")[:8]
    return f"{cleaned} ({short})"


def to_markdown(detail: dict, folder: dict, tags: list[str] | None = None, favorita: bool = False) -> str:
    session = detail.get("session") or {}
    lines = [
        *_front_matter(session, folder, tags or [], favorita),
        "",
        f"# {session.get('title') or '(sem pedido)'}",
        "",
        f"- Folder: {folder.get('label') or folder.get('slug') or ''}",
        f"- Tela: `{session.get('id') or ''}`",
        f"- Início: {session.get('started_at') or '—'}",
        f"- Atualizada: {session.get('updated_at') or '—'}",
        "",
        "Conteúdo de arquivos gravados na conversa não entra neste arquivo: só o caminho.",
        "",
    ]
    final = (session.get("last_comment") or "").strip()
    if final:
        lines.extend(["## Comentário final", "", _quote(final), ""])
    lines.extend(["## Conversa", ""])
    for event in detail.get("events") or []:
        lines.extend(_markdown_event(event))
    if session.get("truncated"):
        lines.extend(
            [
                "",
                f"_Trechos do meio foram omitidos ({session.get('omitted') or 0} eventos)._",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def to_html(detail: dict, folder: dict) -> str:
    session = detail.get("session") or {}
    title = session.get("title") or "(sem pedido)"
    final = (session.get("last_comment") or "").strip()
    final_html = ""
    if final:
        final_html = (
            "<blockquote class=\"final\"><span>Comentário final</span>"
            f"<p>{_paragraphs(final)}</p></blockquote>"
        )
    events = "\n".join(_html_event(event) for event in detail.get("events") or [])
    note = ""
    if session.get("truncated"):
        note = (
            "<p class=\"note\">Trechos do meio foram omitidos "
            f"({int(session.get('omitted') or 0)} eventos).</p>"
        )
    folder_label = html.escape(str(folder.get("label") or folder.get("slug") or ""))
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{ color-scheme: dark; }}
body {{
  margin: 0 auto; max-width: 52rem; padding: 2rem 1.25rem 3rem;
  font: 16px/1.5 "Segoe UI", sans-serif; background: #0f172a; color: #e2e8f0;
}}
h1 {{ font-size: 1.6rem; line-height: 1.3; margin: 0 0 0.75rem; }}
.meta, .note {{ color: #94a3b8; }}
.final {{
  margin: 1.25rem 0; padding: 0.8rem 1rem; border-left: 3px solid #38bdf8;
  background: #1e293b; border-radius: 0.5rem;
}}
.final span {{ display: block; color: #7dd3fc; font-size: 0.8rem; margin-bottom: 0.35rem; }}
.ev {{ margin: 0.85rem 0; padding: 0.75rem 0.9rem; background: #1e293b; border-radius: 0.6rem; }}
.ev header {{ display: flex; gap: 0.75rem; align-items: baseline; margin-bottom: 0.35rem; }}
.tag {{ font-size: 0.75rem; letter-spacing: 0.03em; text-transform: uppercase; color: #7dd3fc; }}
.ev.comment .tag {{ color: #cbd5e1; }}
.ev.command .tag {{ color: #6ee7b7; }}
.ev.tool .tag, .ev.subagent .tag {{ color: #94a3b8; }}
time, .cwd, .detail {{ color: #94a3b8; font-size: 0.85rem; }}
pre {{
  white-space: pre-wrap; word-break: break-word; margin: 0.4rem 0 0;
  font-family: Consolas, monospace; font-size: 0.9rem;
}}
p {{ margin: 0.35rem 0; white-space: pre-wrap; }}
@media print {{
  body {{ background: #fff; color: #111; }}
  .ev, .final {{ background: #f8fafc; }}
}}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p class="meta">Folder: {folder_label}<br>
Tela: {html.escape(str(session.get("id") or ""))}<br>
Início: {html.escape(str(session.get("started_at") or "—"))}<br>
Atualizada: {html.escape(str(session.get("updated_at") or "—"))}</p>
<p class="note">Conteúdo de arquivos gravados na conversa não entra neste arquivo: só o caminho.</p>
{final_html}
{note}
{events}
</body>
</html>
"""


_SUBSTITUTOS = {
    "✅": "[OK]", "❌": "[ERRO]", "⚠": "[AVISO]", "🚫": "[BLOQUEADO]", "🐛": "[BUG]", "💡": "[DICA]", "📌": "[NOTA]",
    "├": "+", "└": "+", "┌": "+", "┐": "+", "┘": "+", "┤": "+", "┬": "+", "┴": "+", "┼": "+",
    "─": "-", "│": "|",
}
_IGNORADOS = "\ufe0e\ufe0f"


def _pdf_texto(texto: str) -> str:
    """Troca caracteres que a fonte do PDF não tem por equivalentes simples."""
    saida = []
    for c in texto:
        if c in _IGNORADOS:
            continue
        if c in _SUBSTITUTOS:
            saida.append(_SUBSTITUTOS[c])
            continue
        o = ord(c)
        if o < 0x0250 or 0x2000 <= o <= 0x206F or c in "€™•…":
            saida.append(c)
        else:
            saida.append("?")
    return "".join(saida)


def _pdf_seguro(valor):
    if isinstance(valor, str):
        return _pdf_texto(valor)
    if isinstance(valor, list):
        return [_pdf_seguro(item) for item in valor]
    if isinstance(valor, dict):
        return {chave: _pdf_seguro(item) for chave, item in valor.items()}
    return valor


def to_pdf(detail: dict, folder: dict) -> bytes:
    detail = _pdf_seguro(detail)
    folder = _pdf_seguro(folder)
    from fpdf import FPDF

    cfg = configuracao_pdf()
    regular, bold, mono = _fonts()
    session = detail.get("session") or {}
    title = session.get("title") or "(sem pedido)"

    class Document(FPDF):
        def header(self):
            if cfg["logo"]:
                self.image(cfg["logo"], x=self.l_margin, y=8, h=10)
            if cfg["cabecalho"]:
                self.set_xy(self.l_margin, 9)
                self.set_font("Body", "B", 8)
                self.set_text_color(71, 85, 105)
                self.cell(self.epw, 6, cfg["cabecalho"], align="R")

        def footer(self):
            self.set_y(-12)
            self.set_font("Body", size=8)
            self.set_text_color(100, 116, 139)
            label = (self.folder_label or "")[:70]
            self.cell(0, 8, f"{label}  ·  {self.page_no()}", align="R")

    pdf = Document(format="A4")
    if cfg["cabecalho"] or cfg["logo"]:
        pdf.set_top_margin(24)
    pdf.folder_label = str(folder.get("label") or folder.get("slug") or "")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_font("Body", "", str(regular))
    pdf.add_font("Body", "B", str(bold))
    pdf.add_font("Mono", "", str(mono))
    pdf.add_page()
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Body", "B", 16)
    pdf.multi_cell(pdf.epw, 8, title, wrapmode="CHAR", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Body", size=10)
    pdf.set_text_color(71, 85, 105)
    meta = (
        f"Folder: {pdf.folder_label}\n"
        f"Tela: {session.get('id') or ''}\n"
        f"Início: {session.get('started_at') or '—'}    Atualizada: {session.get('updated_at') or '—'}\n"
        "Conteúdo de arquivos gravados na conversa não entra neste arquivo: só o caminho."
    )
    pdf.multi_cell(pdf.epw, 5, meta, wrapmode="CHAR", new_x="LMARGIN", new_y="NEXT")
    final = (session.get("last_comment") or "").strip()
    if final:
        pdf.ln(3)
        pdf.set_font("Body", "B", 11)
        pdf.set_text_color(3, 105, 161)
        pdf.multi_cell(pdf.epw, 6, "Comentário final", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Body", size=11)
        pdf.set_text_color(15, 23, 42)
        pdf.multi_cell(pdf.epw, 6, final, wrapmode="CHAR", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Body", "B", 13)
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(pdf.epw, 7, "Conversa", new_x="LMARGIN", new_y="NEXT")
    for event in detail.get("events") or []:
        _pdf_event(pdf, event)
    if session.get("truncated"):
        pdf.ln(2)
        pdf.set_font("Body", size=9)
        pdf.set_text_color(100, 116, 139)
        pdf.multi_cell(
            pdf.epw,
            5,
            f"Trechos do meio foram omitidos ({int(session.get('omitted') or 0)} eventos).",
            new_x="LMARGIN",
            new_y="NEXT",
        )
    return bytes(pdf.output())


def build_download(
    detail: dict,
    folder: dict,
    fmt: str,
    tags: list[str] | None = None,
    favorita: bool = False,
) -> tuple[bytes, str, str]:
    detail = redacao.redact_detail(detail, redacao.load_rules())
    session = detail.get("session") or {}
    stem = file_stem(str(session.get("title") or ""), str(session.get("id") or ""))
    kind = (fmt or "").lower()
    if kind == "html":
        return to_html(detail, folder).encode("utf-8"), f"{stem}.html", "text/html"
    if kind in {"md", "markdown"}:
        return to_markdown(detail, folder, tags, favorita).encode("utf-8"), f"{stem}.md", "text/markdown"
    if kind == "pdf":
        return to_pdf(detail, folder), f"{stem}.pdf", "application/pdf"
    raise ExportError("Formato de exportação desconhecido.")


def events_html(events: list[dict]) -> str:
    if not events:
        return "<p class=\"note\">Nenhum evento neste filtro.</p>"
    return "\n".join(_html_event(event) for event in events)


def _front_matter(session: dict, folder: dict, tags: list[str], favorita: bool) -> list[str]:
    campos = (
        ("titulo", session.get("title") or ""),
        ("sessao", session.get("id") or ""),
        ("pasta", folder.get("label") or folder.get("slug") or ""),
        ("iniciada", session.get("started_at") or ""),
        ("atualizada", session.get("updated_at") or ""),
        ("favorita", favorita),
        ("tags", list(tags)),
    )
    # JSON é YAML válido, então os valores ficam escapados corretamente.
    return ["---", *(f"{chave}: {json.dumps(valor, ensure_ascii=False)}" for chave, valor in campos), "---"]


def _markdown_event(event: dict) -> list[str]:
    label = kind_label(event)
    when = f" · {event['at']}" if event.get("at") else ""
    lines = [f"### {event.get('seq') or ''} · {label}{when}", ""]
    if event.get("detail"):
        lines.extend([_quote(str(event["detail"])), ""])
    text = str(event.get("text") or "")
    if event.get("kind") == "command":
        lines.extend([_indent(text), ""])
    elif text:
        lines.extend([_quote(text), ""])
    if event.get("cwd"):
        lines.extend([f"`{event['cwd']}`", ""])
    if event.get("subagent") and event.get("kind") != "subagent":
        lines.extend([f"_Agente auxiliar {event['subagent']}_", ""])
    return lines


def _html_event(event: dict) -> str:
    kind = html.escape(str(event.get("kind") or "tool"))
    label = html.escape(kind_label(event))
    when = f"<time>{html.escape(str(event['at']))}</time>" if event.get("at") else ""
    detail = (
        f"<p class=\"detail\">{_paragraphs(str(event['detail']))}</p>" if event.get("detail") else ""
    )
    text = str(event.get("text") or "")
    if event.get("kind") == "command":
        body = f"<pre>{html.escape(text)}</pre>"
    elif text:
        body = f"<p>{_paragraphs(text)}</p>"
    else:
        body = ""
    cwd = f"<p class=\"cwd\">{html.escape(str(event['cwd']))}</p>" if event.get("cwd") else ""
    return (
        f"<article class=\"ev {kind}\"><header><span class=\"tag\">{label}</span>{when}</header>"
        f"{detail}{body}{cwd}</article>"
    )


def _pdf_event(pdf, event: dict) -> None:
    pdf.ln(2)
    pdf.set_font("Body", "B", 10)
    pdf.set_text_color(*_pdf_color(event.get("kind")))
    when = f"  ·  {event['at']}" if event.get("at") else ""
    pdf.multi_cell(
        pdf.epw,
        5,
        f"{event.get('seq') or ''}  {kind_label(event)}{when}",
        wrapmode="CHAR",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_text_color(15, 23, 42)
    if event.get("detail"):
        pdf.set_font("Body", size=9)
        pdf.set_text_color(71, 85, 105)
        pdf.multi_cell(pdf.epw, 5, str(event["detail"]), wrapmode="CHAR", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(15, 23, 42)
    text = str(event.get("text") or "")
    if text:
        if event.get("kind") == "command":
            pdf.set_font("Mono", size=9)
        else:
            pdf.set_font("Body", size=11)
        pdf.multi_cell(pdf.epw, 5, text, wrapmode="CHAR", new_x="LMARGIN", new_y="NEXT")
    if event.get("cwd"):
        pdf.set_font("Body", size=8)
        pdf.set_text_color(100, 116, 139)
        pdf.multi_cell(pdf.epw, 4, str(event["cwd"]), wrapmode="CHAR", new_x="LMARGIN", new_y="NEXT")


def _pdf_color(kind: str | None) -> tuple[int, int, int]:
    if kind == "user":
        return (3, 105, 161)
    if kind == "command":
        return (6, 95, 70)
    if kind == "comment":
        return (51, 65, 85)
    return (100, 116, 139)


def configuracao_pdf(caminho: Path = CONFIG_PDF) -> dict:
    """Cabeçalho e logo do PDF, lidos de export.json. O logo pode ser caminho relativo."""
    if not caminho.is_file():
        return {"cabecalho": "", "logo": ""}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise ExportError(f"Não consegui ler {caminho.name}: {erro}") from erro
    logo = str(dados.get("logo") or "").strip()
    if logo:
        arquivo = Path(logo)
        if not arquivo.is_absolute():
            arquivo = caminho.parent / arquivo
        if not arquivo.is_file():
            raise ExportError(f"Logo do PDF não encontrado: {arquivo}")
        logo = str(arquivo)
    return {"cabecalho": str(dados.get("cabecalho") or "").strip(), "logo": logo}


def _fonts() -> tuple[Path, Path, Path]:
    for regular, bold, mono in _FONT_CANDIDATES:
        if regular.is_file() and bold.is_file() and mono.is_file():
            return regular, bold, mono
    raise ExportError(
        "Não encontrei uma fonte com acentos para gerar o PDF "
        "(Segoe UI no Windows ou DejaVu no Linux)."
    )


def _quote(text: str) -> str:
    return "\n".join(f"> {line}" for line in (text.splitlines() or [""]))


def _indent(text: str) -> str:
    return "\n".join(f"    {line}" for line in (text.splitlines() or [""]))


def _paragraphs(text: str) -> str:
    return "<br>".join(html.escape(line) for line in text.splitlines()) or ""
