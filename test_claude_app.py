import struct
import tempfile
import unittest
from pathlib import Path

import claude_app_sessions as claude_app
from cursor_agent_sessions import CursorSessionsError

SID = "adcf1ea0-b1e5-4170-ba4b-cc88f08ec8c6"
SID_TABELA = "b7e1c2d0-4f3a-4b2c-9d1e-0a1b2c3d4e5f"
SID_LOG = "c8f2d3e1-5a4b-4c3d-8e2f-1b2c3d4e5f60"


def _varint(saida: bytearray, numero: int) -> None:
    while numero > 0x7F:
        saida.append((numero & 0x7F) | 0x80)
        numero >>= 7
    saida.append(numero)


def _v8(valor) -> bytes:
    saida = bytearray()

    def escrever(item) -> None:
        if item is None:
            saida.append(ord("0"))
            return
        if isinstance(item, str):
            bruto = item.encode("latin-1")
            saida.append(ord('"'))
            _varint(saida, len(bruto))
            saida.extend(bruto)
            return
        if isinstance(item, list):
            saida.append(ord("A"))
            _varint(saida, len(item))
            for filho in item:
                escrever(filho)
            saida.append(ord("$"))
            _varint(saida, 0)
            _varint(saida, len(item))
            return
        if isinstance(item, dict):
            saida.append(ord("o"))
            for chave, filho in item.items():
                escrever(str(chave))
                escrever(filho)
            saida.append(ord("{"))
            _varint(saida, len(item))
            return
        raise TypeError(type(item))

    escrever(valor)
    return bytes(saida)


def _snappy(dados: bytes) -> bytes:
    saida = bytearray()
    _varint(saida, len(dados))
    pos = 0
    while pos < len(dados):
        bloco = dados[pos : pos + 60]
        saida.append((len(bloco) - 1) << 2)
        saida += bloco
        pos += len(bloco)
    return bytes(saida)


def _chave_idb(identificador: str) -> bytes:
    return b"\x00\x04\x01\x01\x01\x24" + identificador.encode("utf-16le") + b"\x01\x00\x00\x00\x00\x00\x00\x00"


def _entrada(chave: bytes, valor: bytes) -> bytes:
    saida = bytearray()
    _varint(saida, 0)
    _varint(saida, len(chave))
    _varint(saida, len(valor))
    saida += chave
    saida += valor
    return bytes(saida)


def _bloco(pares: list[tuple[bytes, bytes]]) -> bytes:
    corpo = bytearray()
    reinicios = []
    for chave, valor in pares:
        reinicios.append(len(corpo))
        corpo += _entrada(chave, valor)
    for ponto in reinicios:
        corpo += struct.pack("<I", ponto)
    corpo += struct.pack("<I", len(reinicios))
    return _snappy(bytes(corpo))


def _tabela(pares: list[tuple[bytes, bytes]]) -> bytes:
    dados = _bloco(pares)
    handle = bytearray()
    _varint(handle, 0)
    _varint(handle, len(dados))
    indice = _bloco([(pares[-1][0], bytes(handle))])
    rodape = bytearray()
    _varint(rodape, 0)
    _varint(rodape, 0)
    _varint(rodape, len(dados))
    _varint(rodape, len(indice))
    rodape += b"\x00" * (40 - len(rodape))
    rodape += b"\x57\xfb\x80\x8b\x24\x75\x47\xdb"
    return dados + indice + bytes(rodape)


def _registro_log(chave: bytes, valor: bytes) -> bytes:
    lote = bytearray()
    lote += (1).to_bytes(8, "little")
    lote += (1).to_bytes(4, "little")
    lote.append(1)
    _varint(lote, len(chave))
    lote += chave
    _varint(lote, len(valor))
    lote += valor
    cabecalho = (0).to_bytes(4, "little") + len(lote).to_bytes(2, "little") + bytes([1])
    return cabecalho + bytes(lote)


def _conversa(identificador: str = SID, pedidos: int = 1) -> dict:
    mensagens = []
    for indice in range(pedidos):
        mensagens.append(
            {
                "sender": "human",
                "created_at": "2026-11-16T17:50:07.487Z",
                "updated_at": "2026-11-16T17:50:07.487Z",
                "content": [{"type": "text", "text": "Organize as notas" if indice == 0 else f"Pedido {indice}"}],
            }
        )
    mensagens.append(
        {
            "sender": "assistant",
            "created_at": "2026-11-16T17:50:15.270Z",
            "updated_at": "2026-11-16T17:50:15.270Z",
            "content": [
                {"type": "thinking", "thinking": "Vou listar a pasta.", "title": "Pensou por 1s"},
                {"type": "text", "text": "Notas organizadas."},
                {"type": "tool_use", "name": "Bash", "input": {"command": "ls notas", "description": "Lista"}},
                {"type": "tool_result", "content": "nao mostrar este resultado"},
            ],
        }
    )
    return {"conversationUuid": identificador, "tree": {"messages": mensagens}}


class ClaudeAppSessionsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        blob = self.root / "https_claude.ai_0.indexeddb.blob" / "4" / "00" / "b3"
        blob.parent.mkdir(parents=True)
        blob.write_bytes(b"\xff\x11\x02" + _snappy(_v8(_conversa())))

    def tearDown(self):
        self._tmp.cleanup()

    def test_sessoes_aparecem_em_uma_pasta(self):
        pastas = claude_app.list_folders(root=self.root)["folders"]
        self.assertEqual(len(pastas), 1)
        self.assertEqual(pastas[0]["slug"], "claude")
        self.assertEqual(pastas[0]["sessions"], 1)

    def test_resumo_usa_o_primeiro_pedido(self):
        sessao = claude_app.list_sessions("claude", root=self.root)["sessions"][0]
        self.assertEqual(sessao["id"], SID)
        self.assertEqual(sessao["title"], "Organize as notas")
        self.assertEqual(sessao["user_turns"], 1)
        self.assertEqual(sessao["comments"], 1)
        self.assertEqual(sessao["commands"], 1)

    def test_detalhe_separa_pensamento_comando_e_ignora_resultado(self):
        detalhe = claude_app.session_detail("claude", SID, root=self.root)
        tipos = [evento["kind"] for evento in detalhe["events"]]
        self.assertEqual(tipos, ["user", "thinking", "comment", "command"])
        self.assertEqual(detalhe["events"][-1]["text"], "ls notas")
        texto = " ".join(evento["text"] for evento in detalhe["events"])
        self.assertNotIn("nao mostrar", texto)

    def test_sem_arquivos_mostra_aviso(self):
        vazio = Path(tempfile.mkdtemp())
        self.assertEqual(claude_app.list_folders(root=vazio)["folders"], [])

    def test_id_invalido_gera_erro(self):
        with self.assertRaises(CursorSessionsError):
            claude_app.session_detail("claude", "nao-e-uuid", root=self.root)

    def test_tabela_e_log_trazem_as_outras_conversas(self):
        resumo_id = "d9a3e4f2-6b5c-4d4e-9f30-2c3d4e5f6071"
        nivel = self.root / "https_claude.ai_0.indexeddb.leveldb"
        nivel.mkdir()
        (nivel / "000003.ldb").write_bytes(
            _tabela(
                [
                    (_chave_idb(SID), _v8(_conversa(SID, pedidos=2))),
                    (_chave_idb(SID_TABELA), _v8(_conversa(SID_TABELA))),
                    (_chave_idb(resumo_id), _v8({"conversationUuid": resumo_id})),
                ]
            )
        )
        (nivel / "000003.log").write_bytes(_registro_log(_chave_idb(SID_LOG), _v8(_conversa(SID_LOG))))
        sessoes = claude_app.list_sessions("claude", root=self.root)["sessions"]
        por_id = {item["id"]: item for item in sessoes}
        self.assertEqual(set(por_id), {SID, SID_TABELA, SID_LOG})
        self.assertEqual(por_id[SID]["user_turns"], 2)


if __name__ == "__main__":
    unittest.main()
