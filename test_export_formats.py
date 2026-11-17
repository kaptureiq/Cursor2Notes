"""Exportação local de uma conversa, sem Streamlit."""
from __future__ import annotations

import unittest

from export_formats import build_download, file_stem, to_html, to_markdown, to_pdf

DETAIL = {
    "session": {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "title": "Avaliar <safra> do clima",
        "started_at": "2026-11-13T14:13:20",
        "updated_at": "2026-11-13T15:00:00",
        "last_comment": "Janela operacional revisada.",
        "truncated": False,
    },
    "events": [
        {"seq": 1, "kind": "user", "text": "Liste os talhões<script>", "at": "2026-11-13T14:13:20"},
        {
            "seq": 2,
            "kind": "command",
            "tool": "Shell",
            "text": "Get-ChildItem E:\\dados\\" + ("X" * 400),
            "detail": "Listar dados",
            "cwd": "E:\\Github\\meu-projeto",
        },
        {"seq": 3, "kind": "comment", "text": "Encontrei a view exemplo.v_resumo."},
        {"seq": 4, "kind": "tool", "tool": "Read", "text": "services\\api\\views.py"},
    ],
}
FOLDER = {"slug": "e-Github-meu-projeto", "label": "E:\\Github\\meu-projeto", "sessions": 7}


class ExportFormatsTest(unittest.TestCase):
    def test_filename_drops_forbidden_characters(self):
        self.assertEqual(file_stem('a/b:c*?"<>|', "12345678-rest"), "a-b-c (12345678)")

    def test_markdown_quotes_the_request_and_indents_the_command(self):
        text = to_markdown(DETAIL, FOLDER)
        self.assertIn("# Avaliar <safra> do clima", text)
        self.assertIn("E:\\Github\\meu-projeto", text)
        self.assertIn("> Liste os talhões<script>", text)
        self.assertIn("    Get-ChildItem E:\\dados", text)
        self.assertIn("## Comentário final", text)

    def test_html_escapes_markup(self):
        text = to_html(DETAIL, FOLDER)
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("&lt;safra&gt;", text)
        self.assertNotIn("<script>", text)
        self.assertIn("<pre>Get-ChildItem", text)

    def test_pdf_is_a_real_document(self):
        data = to_pdf(DETAIL, FOLDER)
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertGreater(len(data), 800)

    def test_download_names(self):
        html_data, html_name, html_mime = build_download(DETAIL, FOLDER, "html")
        md_data, md_name, md_mime = build_download(DETAIL, FOLDER, "markdown")
        pdf_data, pdf_name, pdf_mime = build_download(DETAIL, FOLDER, "pdf")
        self.assertTrue(html_name.endswith(".html") and html_mime == "text/html")
        self.assertTrue(md_name.endswith(".md") and md_mime == "text/markdown")
        self.assertTrue(pdf_name.endswith(".pdf") and pdf_mime == "application/pdf")
        self.assertIn(b"talh", html_data)
        self.assertIn("talh".encode(), md_data)
        self.assertTrue(pdf_data.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
