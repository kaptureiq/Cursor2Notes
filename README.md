# Cursor2Notes

Consulta local das conversas dos agentes do Cursor, Claude Code, Claude Desktop (Cowork), Claude, VS Code e Antigravity. O aplicativo roda localmente: não sobe servidor, não pede login e não altera as conversas originais.

Na barra lateral, escolha o aplicativo: **Cursor**, **Claude Code**, **Claude Desktop (Cowork)**, **Claude**, **VS Code** ou **Antigravity**. Cada pasta listada corresponde a um projeto deste computador. As pastas temporárias (worktrees e pastas temporárias do Windows) ficam escondidas por padrão nas origens que listam pastas de projeto. A tela lista as conversas dessa pasta, com o pedido, os comandos executados, os comentários e o comentário final. Dá para filtrar a pasta, buscar por pedido, comando ou comentário, e restringir a leitura a pedidos, comentários ou comandos.

A conversa aberta tem três botões de exportação:

- **HTML** — página única, para abrir no navegador ou imprimir
- **Markdown** — texto para arquivar ou colar em outro editor
- **PDF** — documento paginado, com acentos

O arquivo exportado leva a conversa inteira. O corpo de arquivos gravados ou editados na conversa não entra: o registro fica só com o caminho.

Na barra lateral, escolha o idioma da interface e abra a página **Ficha técnica**, que descreve o aplicativo, o stack e as fronteiras de leitura.

## Organização e exportação

- **Favoritas e tags:** marque uma conversa como favorita e atribua tags separadas por vírgula. Na barra lateral, filtre por favoritas ou por tag. Os dados ficam em `metadados.json`, ao lado do app, e as conversas de origem não são alteradas.
- **Front matter no Markdown:** cada `.md` começa com título, sessão, pasta, datas, favorita e tags, para importar no Obsidian ou no Notion sem ajustes.
- **Exportar pasta inteira:** na barra lateral, escolha os formatos e gere um ZIP com todas as conversas da pasta e um `indice.html`. Com "Só conversas novas ou alteradas", o ZIP leva apenas o que mudou desde a última exportação de cada formato.
- **Cabeçalho e logo do PDF:** edite `export.json` com o texto do cabeçalho e o caminho de um logo PNG ou JPG (relativo a esta pasta ou absoluto).
- **Redação de segredos:** antes de qualquer exportação, senhas, tokens, chaves e strings de conexão são trocados por `[REDIGIDO]`. Os padrões embutidos estão em `redacao.py`. Em `redacao.json` você pode adicionar regras próprias ou desativar regras embutidas pelo nome. A tela continua mostrando o texto original.

Para o caminho das conversas, defina a variável da origem quando ela não estiver no local padrão:

- **Cursor:** `CURSOR2NOTES_PROJECTS_ROOT` (padrão `~/.cursor/projects`)
- **Claude Code:** `CLAUDE2NOTES_PROJECTS_ROOT` (padrão `~/.claude/projects`)
- **Claude Desktop (Cowork):** `CLAUDE_DESKTOP2NOTES_ROOT` (padrão `%APPDATA%\Claude\local-agent-mode-sessions`)
- **Claude:** `CLAUDE_APP2NOTES_ROOT` (padrão `%APPDATA%\Claude\IndexedDB`)
- **VS Code:** `VSCODE2NOTES_DB` (padrão `%APPDATA%\Code\User\globalStorage\github.copilot-chat\session-store.db`)
- **Antigravity:** `ANTIGRAVITY2NOTES_ROOT` (padrão `~/.gemini/antigravity`)

## Aparência e idioma

- **Temas:** 18 temas dos grupos Oficiais, Fintech e GeoTech, extraídos do KaptureBOARD e guardados em `temas.json`. O padrão é Kapture SAP. Escolha em **Aparência**, na barra lateral.
- **Idiomas:** português (Brasil), inglês, espanhol, francês (França), francês (Canadá) e alemão. Os textos ficam em `i18n.py`. A troca vale para a interface; os arquivos exportados e as mensagens lidas das conversas continuam em português.

## Testes

Na pasta do aplicativo, com o `.venv` ativo:

```powershell
python -m unittest discover -p "test_*.py"
```

## Instalação

A pasta do aplicativo é autossuficiente. `reader.py` escolhe a origem e os leitores ficam ao lado de `app.py`, então a pasta pode ser copiada para qualquer lugar.

É preciso ter Python 3.11 ou mais recente no PATH.

Na pasta do aplicativo, crie o ambiente virtual, instale as dependências e inicie:

```powershell
cd caminho\para\cursor2notes
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

O `requirements.txt` pede o Streamlit, para a tela, e o fpdf2, para o PDF. O ambiente `.venv` fica só nesta pasta.

O navegador abre em `http://localhost:8501`. Para encerrar, use o botão **Sair** no fim da barra lateral ou Ctrl+C no terminal. Na próxima vez, basta ativar o `.venv` e repetir o `streamlit run`.
