import sqlite3
import tempfile
import unittest
from pathlib import Path

import vscode_sessions as vscode
from cursor_agent_sessions import CursorSessionsError

UM = "11111111-2222-3333-4444-555555555555"
DOIS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _banco(caminho: Path) -> None:
    conexao = sqlite3.connect(caminho)
    conexao.executescript(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            cwd TEXT,
            repository TEXT,
            summary TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_index INTEGER NOT NULL,
            user_message TEXT,
            assistant_response TEXT,
            timestamp TEXT
        );
        """
    )
    conexao.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
        (UM, r"E:\Github\cursor2notes", "cursor2notes", "Exportar notas", "2026-11-16T12:00:00Z", "2026-11-16T12:05:00Z"),
    )
    conexao.execute(
        "INSERT INTO turns (session_id, turn_index, user_message, assistant_response, timestamp) VALUES (?, ?, ?, ?, ?)",
        (UM, 0, "Exporte as notas", "Notas exportadas.", "2026-11-16T12:01:00Z"),
    )
    conexao.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
        (DOIS, r"E:\Github\outro", "", "", "2026-11-16T13:00:00Z", "2026-11-16T13:02:00Z"),
    )
    conexao.execute(
        "INSERT INTO turns (session_id, turn_index, user_message, assistant_response, timestamp) VALUES (?, ?, ?, ?, ?)",
        (DOIS, 0, "Liste a pasta", "Pasta listada.", "2026-11-16T13:01:00Z"),
    )
    conexao.commit()
    conexao.close()


class VsCodeSessionsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "session-store.db"
        _banco(self.db)

    def tearDown(self):
        self._tmp.cleanup()

    def test_pastas_seguem_repositorio_ou_cwd(self):
        pastas = vscode.list_folders(root=self.db)["folders"]
        rotulos = {pasta["label"] for pasta in pastas}
        self.assertEqual(rotulos, {"cursor2notes", r"E:\Github\outro"})
        self.assertTrue(all(pasta["sessions"] == 1 for pasta in pastas))

    def test_resumo_prefere_o_summary(self):
        slug = next(pasta["slug"] for pasta in vscode.list_folders(root=self.db)["folders"] if pasta["label"] == "cursor2notes")
        sessao = vscode.list_sessions(slug, root=self.db)["sessions"][0]
        self.assertEqual(sessao["title"], "Exportar notas")
        self.assertEqual(sessao["user_turns"], 1)
        self.assertEqual(sessao["comments"], 1)

    def test_detalhe_mostra_pedido_e_resposta(self):
        slug = next(pasta["slug"] for pasta in vscode.list_folders(root=self.db)["folders"] if pasta["label"] == "cursor2notes")
        detalhe = vscode.session_detail(slug, UM, root=self.db)
        self.assertEqual([evento["kind"] for evento in detalhe["events"]], ["user", "comment"])
        self.assertEqual(detalhe["events"][0]["text"], "Exporte as notas")
        self.assertEqual(detalhe["events"][1]["text"], "Notas exportadas.")

    def test_banco_ausente_mostra_aviso(self):
        ausente = Path(self._tmp.name) / "nao-existe.db"
        self.assertEqual(vscode.list_folders(root=ausente)["folders"], [])

    def test_id_invalido_gera_erro(self):
        slug = vscode.list_folders(root=self.db)["folders"][0]["slug"]
        with self.assertRaises(CursorSessionsError):
            vscode.session_detail(slug, "nao-e-uuid", root=self.db)


if __name__ == "__main__":
    unittest.main()
