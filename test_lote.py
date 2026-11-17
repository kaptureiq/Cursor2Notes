"""Testes da exportação em lote e da configuração do PDF."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import export_formats
import lote
import metadados

FOLDER = {"slug": "e-projeto", "label": "E:\\projeto"}


def conversa(id_: str, titulo: str, atualizada: str = "2026-11-17") -> tuple[dict, dict]:
    resumo = {"id": id_, "updated_at": atualizada}
    detalhe = {
        "session": {"id": id_, "title": titulo, "updated_at": atualizada, "started_at": atualizada, "last_comment": None},
        "events": [{"seq": 1, "kind": "user", "text": "oi"}],
    }
    return resumo, detalhe


class LoteTest(unittest.TestCase):
    def test_zip_tem_arquivos_e_indice(self):
        dados, gravados = lote.montar_zip(FOLDER, [conversa("aaaa1111", "Primeira")], ["md", "html"], {"conversas": {}}, False)
        nomes = zipfile.ZipFile(io.BytesIO(dados)).namelist()
        self.assertIn("indice.html", nomes)
        self.assertTrue(any(n.startswith("markdown/") for n in nomes))
        self.assertTrue(any(n.startswith("html/") for n in nomes))
        self.assertEqual(len(gravados), 2)

    def test_somente_novas_pula_o_que_nao_mudou(self):
        store = {"conversas": {}}
        resumo, detalhe = conversa("bbbb2222", "Já exportada")
        _, gravados = lote.montar_zip(FOLDER, [(resumo, detalhe)], ["md"], store, False)
        for chave, fmt, atualizada in gravados:
            metadados.registrar_exportacao(store, chave, fmt, atualizada)
        _, segunda = lote.montar_zip(FOLDER, [(resumo, detalhe)], ["md"], store, True)
        self.assertEqual(segunda, [])

    def test_indice_escapa_titulo_e_mostra_favorita_e_tags(self):
        store = {"conversas": {}}
        chave = metadados.chave(FOLDER["slug"], "cccc3333")
        metadados.definir_tags(store, chave, "oracle")
        metadados.alternar_favorita(store, chave)
        dados, _ = lote.montar_zip(FOLDER, [conversa("cccc3333", "<script>x</script>")], ["html"], store, False)
        indice = zipfile.ZipFile(io.BytesIO(dados)).read("indice.html").decode("utf-8")
        self.assertIn("&lt;script&gt;", indice)
        self.assertNotIn("<script>x", indice)
        self.assertIn("#oracle", indice)
        self.assertIn("★", indice)

    def test_lote_mascara_segredos(self):
        resumo, detalhe = conversa("dddd4444", "Teste")
        detalhe["events"] = [{"seq": 1, "kind": "command", "text": "psql postgresql://u:SEGREDO9@h/db"}]
        dados, _ = lote.montar_zip(FOLDER, [(resumo, detalhe)], ["md"], {"conversas": {}}, False)
        self.assertFalse(any(b"SEGREDO9" in zipfile.ZipFile(io.BytesIO(dados)).read(n) for n in zipfile.ZipFile(io.BytesIO(dados)).namelist()))


class ConfiguracaoPdfTest(unittest.TestCase):
    def test_sem_arquivo_usa_valores_vazios(self):
        with tempfile.TemporaryDirectory() as pasta:
            self.assertEqual(
                export_formats.configuracao_pdf(Path(pasta) / "export.json"),
                {"cabecalho": "", "logo": ""},
            )

    def test_logo_inexistente_gera_erro_claro(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "export.json"
            caminho.write_text(json.dumps({"cabecalho": "Cliente X", "logo": "nao-existe.png"}), encoding="utf-8")
            with self.assertRaises(export_formats.ExportError):
                export_formats.configuracao_pdf(caminho)

    def test_logo_relativo_resolve_pela_pasta_do_arquivo(self):
        with tempfile.TemporaryDirectory() as pasta:
            (Path(pasta) / "logo.png").write_bytes(b"\x89PNG")
            caminho = Path(pasta) / "export.json"
            caminho.write_text(json.dumps({"cabecalho": " Cliente X ", "logo": "logo.png"}), encoding="utf-8")
            cfg = export_formats.configuracao_pdf(caminho)
            self.assertEqual(cfg["cabecalho"], "Cliente X")
            self.assertEqual(cfg["logo"], str(Path(pasta) / "logo.png"))


if __name__ == "__main__":
    unittest.main()
