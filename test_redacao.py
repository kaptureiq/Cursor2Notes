"""Testes da redação de segredos."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import redacao


def mascarar(texto: str, path: Path | None = None) -> str:
    regras = redacao.load_rules(path or redacao.CONFIG_PATH)
    return redacao.redact_text(texto, regras)


class RedacaoTest(unittest.TestCase):
    def test_mascara_senha_em_url(self):
        texto = "postgresql://app:s3cr3t@localhost:5432/banco"
        self.assertEqual(mascarar(texto), "postgresql://app:[REDIGIDO]@localhost:5432/banco")

    def test_mascara_usuario_senha_oracle(self):
        self.assertIn("sqlplus scott/[REDIGIDO]@//host:1521/XE", mascarar("sqlplus scott/tigre@//host:1521/XE"))

    def test_mascara_atribuicao_de_ambiente(self):
        self.assertEqual(mascarar('$env:PGPASSWORD="abc123"'), '$env:PGPASSWORD=[REDIGIDO]')

    def test_mascara_valor_em_json(self):
        self.assertEqual(mascarar('{"password": "abc123"}'), '{"password": [REDIGIDO]}')

    def test_mascara_argumento_de_linha_de_comando(self):
        self.assertEqual(mascarar("psql --password=xyz -h db"), "psql --password=[REDIGIDO] -h db")

    def test_mascara_bearer_e_chaves_conhecidas(self):
        self.assertEqual(mascarar("Authorization: Bearer abcdef1234567890"), "Authorization: Bearer [REDIGIDO]")
        self.assertEqual(mascarar("chave AKIAABCDEFGHIJKLMNOP"), "chave [REDIGIDO]")
        self.assertEqual(mascarar("ghp_" + "a" * 36), "[REDIGIDO]")

    def test_nao_altera_texto_comum(self):
        texto = "Liste os talhões de src/app.py e rode git status"
        self.assertEqual(mascarar(texto), texto)

    def test_regra_propria_e_desativacao(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "redacao.json"
            caminho.write_text(
                json.dumps(
                    {
                        "desativar": ["bearer"],
                        "regras": [{"nome": "cpf", "padrao": r"\d{3}\.\d{3}\.\d{3}-\d{2}", "substituicao": "[CPF]"}],
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(mascarar("CPF 123.456.789-09", caminho), "CPF [CPF]")
            self.assertEqual(mascarar("Bearer abcdef1234567890", caminho), "Bearer abcdef1234567890")

    def test_redact_detail_nao_altera_o_original(self):
        detalhe = {
            "session": {"title": "conexão postgresql://u:x@h/db", "last_comment": None},
            "events": [{"kind": "command", "text": "psql postgresql://u:x@h/db"}],
        }
        limpo = redacao.redact_detail(detalhe, redacao.load_rules(Path("/nao/existe.json")))
        self.assertIn("[REDIGIDO]", limpo["session"]["title"])
        self.assertIn("[REDIGIDO]", limpo["events"][0]["text"])
        self.assertIn("x@h", detalhe["events"][0]["text"])


if __name__ == "__main__":
    unittest.main()
