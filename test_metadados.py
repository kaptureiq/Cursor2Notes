"""Testes de tags, favoritos e registro de exportação."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import metadados


class MetadadosTest(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho = Path(self.pasta.name) / "metadados.json"
        self.chave = metadados.chave("e-projeto", "sessao-1")

    def tearDown(self):
        self.pasta.cleanup()

    def test_normaliza_tags(self):
        dados = metadados.carregar(self.caminho)
        tags = metadados.definir_tags(dados, self.chave, " Oracle, #Migração Pg, oracle,, ")
        self.assertEqual(tags, ["oracle", "migração-pg"])

    def test_favorita_alterna_e_persiste(self):
        dados = metadados.carregar(self.caminho)
        self.assertTrue(metadados.alternar_favorita(dados, self.chave))
        metadados.salvar(dados, self.caminho)
        recarregado = metadados.carregar(self.caminho)
        self.assertTrue(metadados.obter(recarregado, self.chave)["favorita"])
        self.assertFalse(metadados.alternar_favorita(recarregado, self.chave))

    def test_precisa_exportar_compara_data_de_atualizacao(self):
        dados = metadados.carregar(self.caminho)
        self.assertTrue(metadados.precisa_exportar(dados, self.chave, "md", "2026-11-17T10:00"))
        metadados.registrar_exportacao(dados, self.chave, "md", "2026-11-17T10:00")
        self.assertFalse(metadados.precisa_exportar(dados, self.chave, "md", "2026-11-17T10:00"))
        self.assertTrue(metadados.precisa_exportar(dados, self.chave, "md", "2026-11-18T09:00"))
        self.assertTrue(metadados.precisa_exportar(dados, self.chave, "pdf", "2026-11-17T10:00"))

    def test_arquivo_invalido_gera_erro_claro(self):
        self.caminho.write_text("[1, 2]", encoding="utf-8")
        with self.assertRaises(metadados.MetadadosError):
            metadados.carregar(self.caminho)


if __name__ == "__main__":
    unittest.main()
