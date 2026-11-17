"""Exportação em lote de uma pasta do Cursor, em ZIP com índice HTML."""
from __future__ import annotations

import html
import io
import zipfile
from urllib.parse import quote

import metadados
import redacao
from export_formats import build_download

PASTAS = {"html": "html", "md": "markdown", "pdf": "pdf"}


def montar_zip(
    folder: dict,
    conversas: list[tuple[dict, dict]],
    formatos: list[str],
    store: dict,
    somente_novas: bool,
) -> tuple[bytes, list[tuple[str, str, str]]]:
    """Gera o ZIP e devolve também (chave, formato, atualizada_em) de cada arquivo gravado.

    `conversas` é uma lista de (resumo, detalhe completo). Com `somente_novas`,
    só entram os pares conversa/formato que mudaram desde a última exportação.
    """
    regras = redacao.load_rules()
    gravados: list[tuple[str, str, str]] = []
    indice: list[tuple[dict, dict, str]] = []
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for resumo, detalhe in conversas:
            chave = metadados.chave(folder["slug"], resumo["id"])
            atualizada = resumo.get("updated_at") or ""
            registro = metadados.obter(store, chave)
            primeiro = ""
            for fmt in formatos:
                if somente_novas and not metadados.precisa_exportar(store, chave, fmt, atualizada):
                    continue
                dados, nome, _ = build_download(detalhe, folder, fmt, registro["tags"], registro["favorita"])
                caminho = f"{PASTAS[fmt]}/{nome}"
                zf.writestr(caminho, dados)
                gravados.append((chave, fmt, atualizada))
                primeiro = primeiro or caminho
            if primeiro:
                sessao = redacao.redact_detail({"session": detalhe.get("session") or {}}, regras)["session"]
                indice.append((sessao, registro, primeiro))
        zf.writestr("indice.html", _indice_html(folder, indice))
    return buffer.getvalue(), gravados


def _indice_html(folder: dict, itens: list[tuple[dict, dict, str]]) -> str:
    linhas = []
    for sessao, registro, caminho in itens:
        titulo = html.escape(sessao.get("title") or "(sem pedido)")
        href = quote(caminho)
        fav = "★" if registro["favorita"] else ""
        tags = " ".join(f"#{html.escape(tag)}" for tag in registro["tags"])
        atualizada = html.escape(str(sessao.get("updated_at") or ""))
        linhas.append(
            f"<tr><td><a href=\"{href}\">{titulo}</a></td><td>{atualizada}</td>"
            f"<td>{fav}</td><td>{tags}</td></tr>"
        )
    corpo = "\n".join(linhas) or "<tr><td colspan=\"4\">Nenhuma conversa nova ou alterada.</td></tr>"
    pasta = html.escape(str(folder.get("label") or folder.get("slug") or ""))
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Índice · {pasta}</title>
<style>
body {{ font: 15px/1.5 "Segoe UI", sans-serif; margin: 2rem auto; max-width: 56rem; padding: 0 1rem; color: #0f172a; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ text-align: left; padding: 0.5rem; border-bottom: 1px solid #e2e8f0; }}
th {{ color: #475569; font-size: 0.85rem; }}
.meta {{ color: #64748b; }}
</style>
</head>
<body>
<h1>Conversas do Cursor</h1>
<p class="meta">Pasta: {pasta}<br>Gerado em {html.escape(_agora())}</p>
<table>
<thead><tr><th>Pedido</th><th>Atualizada</th><th>Fav.</th><th>Tags</th></tr></thead>
<tbody>
{corpo}
</tbody>
</table>
</body>
</html>
"""


def _agora() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M")
