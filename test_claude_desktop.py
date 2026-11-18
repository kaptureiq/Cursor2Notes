import json
import tempfile
import unittest
from pathlib import Path

import claude_desktop_sessions as desktop
from cursor_agent_sessions import CursorSessionsError

SID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
AUDIT = {"_audit_hmac": "x", "_audit_timestamp": "2026-11-10T12:00:00Z", "session_id": SID, "parent_tool_use_id": None}


def _linhas() -> list[dict]:
    return [
        {"type": "system", "subtype": "init", **AUDIT},
        {"type": "user", "uuid": "1", "message": {"role": "user", "content": "Organize as notas"}, **AUDIT},
        {"type": "assistant", "uuid": "2", "message": {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "Vou listar a pasta."},
            {"type": "text", "text": "Feito, as notas estão organizadas."},
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls notas", "description": "Lista"}},
            {"type": "image", "source": {"type": "base64", "data": "AAAA"}},
        ]}, **AUDIT},
        {"type": "user", "uuid": "3", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t", "content": "ok"}]}, **AUDIT},
        {"type": "result", "subtype": "success", **AUDIT},
    ]


class ClaudeDesktopSessionsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        pasta = self.root / "conta" / "org" / f"local_{SID}"
        pasta.mkdir(parents=True)
        (pasta / "audit.jsonl").write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in _linhas()), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_sessoes_aparecem_em_uma_pasta(self):
        pastas = desktop.list_folders(root=self.root)["folders"]
        self.assertEqual(len(pastas), 1)
        self.assertEqual(pastas[0]["sessions"], 1)

    def test_resumo_usa_primeiro_pedido_como_titulo(self):
        sessao = desktop.list_sessions("cowork", root=self.root)["sessions"][0]
        self.assertEqual(sessao["id"], SID)
        self.assertEqual(sessao["title"], "Organize as notas")
        self.assertEqual(sessao["commands"], 1)

    def test_detalhe_mantem_pensamento_e_ignora_imagem_e_resultados(self):
        detalhe = desktop.session_detail("cowork", SID, root=self.root)
        self.assertEqual([e["kind"] for e in detalhe["events"]], ["user", "thinking", "comment", "command"])

    def test_sem_arquivos_mostra_aviso(self):
        vazio = Path(tempfile.mkdtemp())
        self.assertEqual(desktop.list_folders(root=vazio)["folders"], [])

    def test_id_invalido_gera_erro(self):
        with self.assertRaises(CursorSessionsError):
            desktop.session_detail("cowork", "nao-e-uuid", root=self.root)


if __name__ == "__main__":
    unittest.main()
