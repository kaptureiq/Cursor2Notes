# Telas do Cursor

<img width="2172" height="724" alt="Cursor2Notes_ Exportação Inteligente" src="https://github.com/user-attachments/assets/f9b55099-8645-4d0d-bc1a-7270277d3a0e" />

Consulta local das conversas do agente do Cursor. O aplicativo é independente.

Cada Folder aberto no Cursor corresponde a uma pasta deste computador. A tela lista as conversas desse Folder, com o pedido, os comandos executados, os comentários e o comentário final. Dá para filtrar a pasta, buscar por pedido, comando ou comentário, e restringir a leitura a pedidos, comentários ou comandos.

A conversa aberta tem três botões de exportação:

- **HTML** — página única, para abrir no navegador ou imprimir
- **Markdown** — texto para arquivar ou colar em outro editor
- **PDF** — documento paginado, com acentos

O arquivo exportado leva a conversa inteira. O corpo de arquivos gravados ou editados na conversa não entra: o registro fica só com o caminho.

## Instalação

A pasta do aplicativo é autossuficiente. O leitor das conversas está em `cursor_agent_sessions.py`, ao lado de `app.py`, então a pasta pode ser copiada para qualquer lugar.

É preciso ter Python 3.11 ou mais recente no PATH.

Na pasta do aplicativo, crie o ambiente virtual, instale as dependências e inicie:

```powershell
cd c:\cursor2notes
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

O `requirements.txt` pede o Streamlit, para a tela, e o fpdf2, para o PDF. O ambiente `.venv` fica só nesta pasta.

O navegador abre em `http://localhost:8501`. Para encerrar, use Ctrl+C no terminal. Na próxima vez, basta ativar o `.venv` e repetir o `streamlit run`.

#cursor, #streamlit, #markdown, #pdf-export
