import json
import tempfile
import unittest
from pathlib import Path

import claude_code_sessions as claude
from cursor_agent_sessions import CursorSessionsError

SID = "11111111-2222-3333-4444-555555555555"
SUB = "66666666-7777-8888-9999-000000000000"


def _linhas(sessao: str = SID) -> list[dict]:
    cwd = "E:\\Github\\exemplo"
    return [
        {"type": "user", "message": {"role": "user", "content": "Crie o script de backup"},
         "timestamp": "2026-11-10T12:00:00.000Z", "sessionId": sessao, "cwd": cwd},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "Preciso ler o projeto antes."},
            {"type": "text", "text": "Vou criar o script."},
            {"type": "tool_use", "name": "Bash", "input": {"command": "dir", "description": "Lista arquivos"}},
            {"type": "tool_use", "name": "Write", "input": {"file_path": "backup.py", "contents": "x"}},
        ]}, "timestamp": "2026-11-10T12:00:05.000Z", "sessionId": sessao, "cwd": cwd},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t", "content": "ok"}]},
         "timestamp": "2026-11-10T12:00:06.000Z", "sessionId": sessao},
        {"type": "ai-title", "aiTitle": "Script de backup", "sessionId": sessao},
    ]


def _grava(caminho: Path, linhas: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("\n".join(json.dumps(linha, ensure_ascii=False) for linha in linhas), encoding="utf-8")


class ClaudeCodeSessionsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _grava(self.root / "E--Github-exemplo" / f"{SID}.jsonl", _linhas())
        _grava(self.root / "C--Users-x-AppData-Local-Temp-agdev-worktrees-1" / f"{SID}.jsonl", _linhas())

    def tearDown(self):
        self._tmp.cleanup()

    def test_pastas_temporarias_ficam_escondidas_por_padrao(self):
        pastas = claude.list_folders(root=self.root)["folders"]
        self.assertEqual([p["slug"] for p in pastas], ["E--Github-exemplo"])
        self.assertEqual(pastas[0]["label"], "E:\\Github\\exemplo")

        todas = claude.list_folders(include_temporary=True, root=self.root)["folders"]
        self.assertEqual(len(todas), 2)

    def test_resumo_usa_titulo_da_ia_e_conta_eventos(self):
        sessao = claude.list_sessions("E--Github-exemplo", root=self.root)["sessions"][0]
        self.assertEqual(sessao["title"], "Script de backup")
        self.assertEqual(sessao["user_turns"], 1)
        self.assertEqual(sessao["comments"], 1)
        self.assertEqual(sessao["commands"], 1)
        self.assertEqual(sessao["last_comment"], "Vou criar o script.")

    def test_detalhe_mantem_pensamento_e_ignora_resultados_de_ferramenta(self):
        detalhe = claude.session_detail("E--Github-exemplo", SID, root=self.root)
        tipos = [evento["kind"] for evento in detalhe["events"]]
        self.assertEqual(tipos, ["user", "thinking", "comment", "command", "tool"])
        self.assertEqual(detalhe["events"][-1]["text"], "Write: backup.py")

    def test_subagentes_aparecem_no_detalhe(self):
        _grava(self.root / "E--Github-exemplo" / SID / "subagents" / f"{SUB}.jsonl", _linhas(SUB)[:2])
        detalhe = claude.session_detail("E--Github-exemplo", SID, root=self.root)
        self.assertEqual(detalhe["session"]["subagents"], 1)
        marcadores = [e for e in detalhe["events"] if e["kind"] == "subagent"]
        self.assertEqual(len(marcadores), 1)
        self.assertTrue(any(e["subagent"] == SUB for e in detalhe["events"]))

    def test_id_invalido_gera_erro(self):
        with self.assertRaises(CursorSessionsError):
            claude.session_detail("E--Github-exemplo", "nao-e-uuid", root=self.root)


if __name__ == "__main__":
    unittest.main()
