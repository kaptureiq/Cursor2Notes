import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import antigravity_sessions as ag
import reader
from cursor_agent_sessions import CursorSessionsError

SESSAO_1 = "11111111-2222-3333-4444-555555555555"
SESSAO_2 = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
SUBAGENTE_1 = "99999999-8888-7777-6666-555555555555"


def _criar_transcricao(caminho: Path, linhas: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as f:
        for linha in linhas:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")


def _criar_banco(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE conversation_summaries (
            conversation_id text PRIMARY KEY,
            title text NOT NULL DEFAULT "",
            preview text NOT NULL DEFAULT "",
            step_count integer NOT NULL DEFAULT 0,
            last_modified_time datetime NOT NULL,
            workspace_uris text NOT NULL,
            status text NOT NULL DEFAULT "",
            source text NOT NULL DEFAULT "",
            project_id text NOT NULL DEFAULT "",
            agent_name text NOT NULL DEFAULT "",
            parent_conversation_id text NOT NULL DEFAULT ""
        )
        """
    )
    conn.execute(
        """
        INSERT INTO conversation_summaries
        (conversation_id, title, preview, step_count, last_modified_time, workspace_uris, parent_conversation_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            SESSAO_1,
            "Criar suporte ao Antigravity",
            "Criar suporte ao Antigravity",
            10,
            "2026-11-18 10:00:00",
            json.dumps(["file:///e%3A/Github/cursor2notes"]),
            "",
        ),
    )
    conn.execute(
        """
        INSERT INTO conversation_summaries
        (conversation_id, title, preview, step_count, last_modified_time, workspace_uris, parent_conversation_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            SUBAGENTE_1,
            "Pesquisador de código",
            "Pesquisador de código",
            5,
            "2026-11-18 10:01:00",
            json.dumps(["file:///e%3A/Github/cursor2notes"]),
            SESSAO_1,
        ),
    )
    conn.execute(
        """
        INSERT INTO conversation_summaries
        (conversation_id, title, preview, step_count, last_modified_time, workspace_uris, parent_conversation_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            SESSAO_2,
            "Geral Antigravity",
            "Geral Antigravity",
            2,
            "2026-11-18 11:00:00",
            "[]",
            "",
        ),
    )
    conn.commit()
    conn.close()


def _linhas_sessao_1() -> list[dict]:
    return [
        {
            "step_index": 0,
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "created_at": "2026-11-18T10:00:00Z",
            "content": "<USER_REQUEST>\nAdicione suporte ao Antigravity no cursor2notes\n</USER_REQUEST>\n<ADDITIONAL_METADATA>\ntime: 2026-11-18\n</ADDITIONAL_METADATA>",
        },
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "created_at": "2026-11-18T10:00:05Z",
            "thinking": "Preciso inspecionar o código do projeto.",
            "tool_calls": [
                {
                    "name": "run_command",
                    "args": {"CommandLine": "dir", "toolSummary": "Listar arquivos", "Cwd": "E:\\Github\\cursor2notes"},
                }
            ],
        },
        {
            "step_index": 2,
            "source": "MODEL",
            "type": "GENERIC",
            "created_at": "2026-11-18T10:00:10Z",
            "content": "output do dir que deve ser ignorado",
        },
        {
            "step_index": 3,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "created_at": "2026-11-18T10:00:15Z",
            "content": "Analisei o projeto e vou ler os arquivos.",
            "tool_calls": [
                {
                    "name": "read_file",
                    "args": {"Path": "E:\\Github\\cursor2notes\\README.md"},
                },
                {
                    "name": "invoke_subagent",
                    "args": {"Role": "Codebase Researcher", "Prompt": "Pesquisar módulos"},
                },
            ],
        },
    ]


def _linhas_subagente_1() -> list[dict]:
    return [
        {
            "step_index": 0,
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "created_at": "2026-11-18T10:01:00Z",
            "content": "Pesquisar módulos do repositório",
        },
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "created_at": "2026-11-18T10:01:05Z",
            "content": "Módulos mapeados com sucesso.",
        },
    ]


def _linhas_sessao_2() -> list[dict]:
    return [
        {
            "step_index": 0,
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "created_at": "2026-11-18T11:00:00Z",
            "content": "Ajuda geral sem tags",
        },
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "created_at": "2026-11-18T11:00:05Z",
            "content": "Aqui está a ajuda solicitada.",
        },
    ]


class AntigravitySessionsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.brain = self.root / "brain"
        self.db = self.root / "conversation_summaries.db"

        _criar_banco(self.db)
        _criar_transcricao(
            self.brain / SESSAO_1 / ".system_generated" / "logs" / "transcript_full.jsonl",
            _linhas_sessao_1(),
        )
        _criar_transcricao(
            self.brain / SUBAGENTE_1 / ".system_generated" / "logs" / "transcript.jsonl",
            _linhas_subagente_1(),
        )
        _criar_transcricao(
            self.brain / SESSAO_2 / ".system_generated" / "logs" / "transcript_full.jsonl",
            _linhas_sessao_2(),
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_fonte_registrada_no_reader(self):
        self.assertIs(reader.fonte("antigravity"), ag)

    def test_pastas_ausentes(self):
        vazio = self.root / "inexistente"
        res = ag.list_folders(root=vazio)
        self.assertEqual(res["folders"], [])
        self.assertIn("Nenhuma conversa do Antigravity encontrada", res["note"])

    def test_list_folders_com_banco_e_transcricoes(self):
        pastas = ag.list_folders(root=self.root)["folders"]
        labels = {p["label"] for p in pastas}
        self.assertIn(r"e:\Github\cursor2notes", labels)
        self.assertIn("Antigravity", labels)

        pasta_proj = next(p for p in pastas if p["label"] == r"e:\Github\cursor2notes")
        self.assertEqual(pasta_proj["sessions"], 1)
        self.assertEqual(pasta_proj["kind"], "workspace")

    def test_list_folders_sem_banco_usa_apenas_brain(self):
        tmp_sem_db = tempfile.TemporaryDirectory()
        try:
            brain_solo = Path(tmp_sem_db.name) / "brain"
            _criar_transcricao(
                brain_solo / SESSAO_2 / ".system_generated" / "logs" / "transcript_full.jsonl",
                _linhas_sessao_2(),
            )
            pastas = ag.list_folders(root=Path(tmp_sem_db.name))["folders"]
            self.assertEqual(len(pastas), 1)
            self.assertEqual(pastas[0]["label"], "Antigravity")
            self.assertEqual(pastas[0]["sessions"], 1)
        finally:
            tmp_sem_db.cleanup()

    def test_list_sessions_resumo(self):
        pastas = ag.list_folders(root=self.root)["folders"]
        slug_proj = next(p["slug"] for p in pastas if p["label"] == r"e:\Github\cursor2notes")
        res = ag.list_sessions(slug_proj, root=self.root)
        sessoes = res["sessions"]
        self.assertEqual(len(sessoes), 1)

        sessao = sessoes[0]
        self.assertEqual(sessao["id"], SESSAO_1)
        self.assertEqual(sessao["title"], "Criar suporte ao Antigravity")
        self.assertEqual(sessao["user_turns"], 1)
        self.assertEqual(sessao["comments"], 1)
        self.assertEqual(sessao["commands"], 1)
        self.assertEqual(sessao["subagents"], 1)
        self.assertEqual(sessao["last_comment"], "Analisei o projeto e vou ler os arquivos.")
        self.assertEqual(sessao["command_preview"], ["dir"])

    def test_session_detail_eventos_e_subagente(self):
        pastas = ag.list_folders(root=self.root)["folders"]
        slug_proj = next(p["slug"] for p in pastas if p["label"] == r"e:\Github\cursor2notes")
        detalhe = ag.session_detail(slug_proj, SESSAO_1, root=self.root)

        events = detalhe["events"]
        # Esperado:
        # 1. user (Adicione suporte...)
        # 2. thinking (Preciso inspecionar...)
        # 3. command (dir)
        # 4. comment (Analisei o projeto...)
        # 5. tool (read_file)
        # 6. subagent (invoke_subagent)
        # 7. marcador de subagente
        # 8. user do subagente
        # 9. comment do subagente
        kinds = [e["kind"] for e in events]
        self.assertEqual(
            kinds,
            ["user", "thinking", "command", "comment", "tool", "subagent", "subagent", "user", "comment"],
        )

        self.assertEqual(events[0]["text"], "Adicione suporte ao Antigravity no cursor2notes")
        self.assertEqual(events[1]["text"], "Preciso inspecionar o código do projeto.")
        self.assertEqual(events[2]["text"], "dir")
        self.assertEqual(events[2]["detail"], "Listar arquivos")
        self.assertEqual(events[2]["cwd"], "E:\\Github\\cursor2notes")
        self.assertEqual(events[4]["text"], "read_file: E:\\Github\\cursor2notes\\README.md")

        # Subagente
        sub_events = [e for e in events if e.get("subagent") == SUBAGENTE_1]
        self.assertEqual(len(sub_events), 2)
        self.assertEqual(sub_events[0]["text"], "Pesquisar módulos do repositório")
        self.assertEqual(sub_events[1]["text"], "Módulos mapeados com sucesso.")

        # Sequência numerada
        self.assertEqual([e["seq"] for e in events], list(range(1, len(events) + 1)))

    def test_session_detail_sem_tags_usa_texto_direto(self):
        pastas = ag.list_folders(root=self.root)["folders"]
        slug_geral = next(p["slug"] for p in pastas if p["label"] == "Antigravity")
        detalhe = ag.session_detail(slug_geral, SESSAO_2, root=self.root)
        self.assertEqual(detalhe["events"][0]["text"], "Ajuda geral sem tags")
        self.assertEqual(detalhe["events"][1]["text"], "Aqui está a ajuda solicitada.")

    def test_exportacao_antigravity_formatos(self):
        from export_formats import build_download

        pastas = ag.list_folders(root=self.root)["folders"]
        pasta_proj = next(p for p in pastas if p["label"] == r"e:\Github\cursor2notes")
        detalhe = ag.session_detail(pasta_proj["slug"], SESSAO_1, root=self.root, full=True)

        for fmt in ("html", "md", "pdf"):
            dados, nome, mime = build_download(detalhe, pasta_proj, fmt, tags=["teste"], favorita=True)
            self.assertTrue(len(dados) > 0)
            self.assertTrue(nome.endswith(f".{fmt if fmt != 'markdown' else 'md'}"))
            self.assertTrue(len(mime) > 0)

    def test_validacao_de_ids_e_pastas(self):
        pastas = ag.list_folders(root=self.root)["folders"]
        slug_proj = pastas[0]["slug"]

        with self.assertRaises(CursorSessionsError):
            ag.list_sessions("pasta-inexistente-12345", root=self.root)

        with self.assertRaises(CursorSessionsError):
            ag.session_detail(slug_proj, "id-invalido", root=self.root)

        with self.assertRaises(CursorSessionsError):
            ag.session_detail(slug_proj, "00000000-0000-0000-0000-000000000000", root=self.root)


if __name__ == "__main__":
    unittest.main()
