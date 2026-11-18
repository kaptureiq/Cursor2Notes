import unittest

from export_formats import _pdf_texto, to_pdf


class PdfTextoTest(unittest.TestCase):
    def test_simbolos_e_arvore_viram_ascii(self):
        self.assertEqual(_pdf_texto("✅ ok ├─ x │ y"), "[OK] ok +- x | y")

    def test_acentos_portugueses_ficam(self):
        self.assertEqual(_pdf_texto("ação Ç é º €"), "ação Ç é º €")

    def test_emoji_sem_mapa_vira_interrogacao(self):
        self.assertEqual(_pdf_texto("x🎉y"), "x?y")

    def test_pdf_com_simbolos_gera_arquivo(self):
        detalhe = {"session": {"title": "⚠ teste ├─"}, "events": [{"kind": "command", "text": "🐛 ls ─", "seq": 1, "at": "", "detail": "", "tool": "Shell"}]}
        pasta = {"slug": "x", "label": "✅ pasta"}
        self.assertTrue(to_pdf(detalhe, pasta).startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
